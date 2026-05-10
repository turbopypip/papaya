package createPost

import (
	"context"
	"net/http"
	"time"
	"vkid-backend/internal/cache"
	"vkid-backend/internal/storage"
	"vkid-backend/internal/storage/models"

	"github.com/gin-gonic/gin"
	"github.com/gofrs/uuid"
)

func CreatePost(c *gin.Context) {
	var body struct {
		Content  string    `json:"content"`
		ThreadId uuid.UUID `json:"thread_id"`
	}

	// check if body exists
	if err := c.ShouldBindJSON(&body); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error":   "Failed to get body",
			"details": err.Error(),
		})
		return
	}

	// init post id
	postId, err := uuid.NewV6()
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error":       err.Error(),
			"description": "Failed to generate thread id",
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

	// save post
	result := storage.DB.Create(&post)
	if result.Error != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"message": "Failed to create post",
		})
		return
	}

	if cache.IsGlobalCacheReady() {
		ctx, cancel := context.WithTimeout(c.Request.Context(), 5*time.Second)
		defer cancel()

		forumCache := cache.GetGlobalForumCache()

		// Инвалидируем кэш темы (так как в ней появился новый пост)
		if err := forumCache.InvalidateThread(ctx, body.ThreadId.String()); err != nil {
			// Логируем ошибку, но не прерываем выполнение
			c.Header("Cache-Warning", "Failed to invalidate thread cache")
		}

		// Кэшируем новый пост
		if err := forumCache.CachePost(ctx, postId.String(), post); err != nil {
			c.Header("Cache-Warning", "Failed to cache new post")
		}
	}

	c.JSON(http.StatusOK, gin.H{
		"message": "created post",
		"post":    post,
	})
}
