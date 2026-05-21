package createPost

import (
	"context"
	"net/http"
	"papaya-backend/internal/analytics"
	"papaya-backend/internal/attachments"
	"papaya-backend/internal/cache"
	"papaya-backend/internal/forumvalidation"
	"papaya-backend/internal/realtime"
	"papaya-backend/internal/storage"
	"papaya-backend/internal/storage/models"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/gofrs/uuid"
	"gorm.io/gorm"
)

func CreatePost(c *gin.Context) {
	var body struct {
		Content  string    `json:"content"`
		ThreadId uuid.UUID `json:"thread_id"`
	}

	if strings.HasPrefix(c.GetHeader("Content-Type"), "multipart/form-data") {
		body.Content = c.PostForm("content")
		threadID, err := uuid.FromString(c.PostForm("thread_id"))
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Некорректный идентификатор треда"})
			return
		}
		body.ThreadId = threadID
	} else if err := c.ShouldBindJSON(&body); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Не удалось прочитать данные поста",
		})
		return
	}
	if err := forumvalidation.ValidatePostContent(body.Content); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// init post id
	postId, err := uuid.NewV6()
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Не удалось создать идентификатор поста",
		})
		return
	}

	// load user from context, it should exist after authentication
	user, _ := c.Get("user")
	userData := user.(models.User)

	// init post
	post := models.Post{
		Id:       postId,
		Content:  body.Content,
		UserId:   userData.Id,
		ThreadId: body.ThreadId,
	}

	var savedFiles []string
	err = storage.DB.Transaction(func(tx *gorm.DB) error {
		if err := tx.Create(&post).Error; err != nil {
			return err
		}

		createdAttachments, paths, err := attachments.CreateFromRequest(
			c,
			tx,
			attachments.OwnerTypePost,
			post.Id,
			userData.Id,
		)
		savedFiles = append(savedFiles, paths...)
		if err != nil {
			return err
		}

		post.Attachments = createdAttachments
		return nil
	})
	if err != nil {
		attachments.CleanupFiles(savedFiles)
		if attachments.IsValidationError(err) {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{
			"message": "Не удалось создать пост",
		})
		return
	}
	post.Author = models.PublicUser{
		Id:       userData.Id,
		Username: userData.Username,
	}

	if cache.IsGlobalCacheReady() {
		ctx, cancel := context.WithTimeout(c.Request.Context(), 5*time.Second)
		defer cancel()

		forumCache := cache.GetGlobalForumCache()

		// Инвалидируем кэш темы (так как в ней появился новый пост)
		if err := forumCache.InvalidateThread(ctx, body.ThreadId.String()); err != nil {
			// Логируем ошибку, но не прерываем выполнение
			c.Header("Cache-Warning", "Не удалось обновить кеш треда")
		}

		// Кэшируем новый пост
		if err := forumCache.CachePost(ctx, postId.String(), post); err != nil {
			c.Header("Cache-Warning", "Не удалось обновить кеш поста")
		}
	}

	realtime.DefaultHub.Publish(body.ThreadId.String(), realtime.Event{
		Type:     realtime.EventPostCreated,
		ThreadID: body.ThreadId.String(),
		PostID:   postId.String(),
	})

	analytics.Record(c.Request.Context(), analytics.Event{
		UserID:     userData.Id,
		EventType:  analytics.EventPostCreated,
		EntityType: analytics.EntityPost,
		EntityID:   post.Id,
		ThreadID:   post.ThreadId,
		Metadata: map[string]any{
			"attachments_count": len(post.Attachments),
		},
	})

	c.JSON(http.StatusOK, gin.H{
		"message": "Пост создан",
		"post":    post,
	})
}
