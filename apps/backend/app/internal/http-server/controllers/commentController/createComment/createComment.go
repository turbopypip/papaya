package createComment

import (
	"github.com/gin-gonic/gin"
	"github.com/gofrs/uuid"
	"gorm.io/gorm"
	"net/http"
	"papaya-backend/internal/analytics"
	"papaya-backend/internal/attachments"
	"papaya-backend/internal/forumvalidation"
	"papaya-backend/internal/realtime"
	"papaya-backend/internal/storage"
	"papaya-backend/internal/storage/models"
	"strings"
)

func CreateComment(c *gin.Context) {
	var body struct {
		Content string    `json:"content"`
		PostId  uuid.UUID `json:"post_id"`
	}

	if strings.HasPrefix(c.GetHeader("Content-Type"), "multipart/form-data") {
		body.Content = c.PostForm("content")
		postID, err := uuid.FromString(c.PostForm("post_id"))
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Некорректный идентификатор поста"})
			return
		}
		body.PostId = postID
	} else if err := c.ShouldBindJSON(&body); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Не удалось прочитать данные комментария",
		})
		return
	}
	if err := forumvalidation.ValidateCommentContent(body.Content); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// init comment id
	commentId, err := uuid.NewV6()
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Не удалось создать идентификатор комментария",
		})
		return
	}

	// load user from context, it should exist after authentication
	user, _ := c.Get("user")
	userData := user.(models.User)

	// init Comment
	comment := models.Comment{
		Id:      commentId,
		Content: body.Content,
		UserId:  userData.Id,
		PostId:  body.PostId,
	}

	var savedFiles []string
	err = storage.DB.Transaction(func(tx *gorm.DB) error {
		if err := tx.Create(&comment).Error; err != nil {
			return err
		}

		createdAttachments, paths, err := attachments.CreateFromRequest(
			c,
			tx,
			attachments.OwnerTypeComment,
			comment.Id,
			userData.Id,
		)
		savedFiles = append(savedFiles, paths...)
		if err != nil {
			return err
		}

		comment.Attachments = createdAttachments
		return nil
	})
	if err != nil {
		attachments.CleanupFiles(savedFiles)
		if attachments.IsValidationError(err) {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Не удалось создать комментарий",
		})
		return
	}
	comment.Author = models.PublicUser{
		Id:       userData.Id,
		Username: userData.Username,
	}

	var post models.Post
	if err := storage.DB.First(&post, "id = ?", body.PostId).Error; err == nil {
		realtime.DefaultHub.Publish(post.ThreadId.String(), realtime.Event{
			Type:      realtime.EventCommentCreated,
			ThreadID:  post.ThreadId.String(),
			PostID:    body.PostId.String(),
			CommentID: commentId.String(),
		})
		analytics.Record(c.Request.Context(), analytics.Event{
			UserID:     userData.Id,
			EventType:  analytics.EventCommentCreated,
			EntityType: analytics.EntityComment,
			EntityID:   comment.Id,
			ThreadID:   post.ThreadId,
			Metadata: map[string]any{
				"post_id":           body.PostId.String(),
				"attachments_count": len(comment.Attachments),
			},
		})
	}

	c.JSON(http.StatusOK, gin.H{
		"message": "Комментарий создан",
		"comment": comment,
	})
}
