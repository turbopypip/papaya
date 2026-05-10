package createThread

import (
	"context"
	"net/http"
	"papaya-backend/internal/cache"
	"papaya-backend/internal/storage"
	"papaya-backend/internal/storage/models"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/gofrs/uuid"
)

func CreateThread(c *gin.Context) {
	var body struct {
		Title      string   `json:"title"`
		Categories []string `json:"categories"`
	}

	if err := c.ShouldBindJSON(&body); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error":   "Failed to get body",
			"details": err.Error(),
		})
		return
	}

	// init thread id
	threadId, err := uuid.NewV6()
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

	// init thread
	thread := models.Thread{
		Id:         threadId,
		Title:      body.Title,
		Categories: body.Categories,
		UserId:     userData.Id,
	}

	// save thread
	result := storage.DB.Create(&thread)
	if result.Error != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"message": "Failed to create thread",
		})
		return
	}

	// Кэшируем новую тему
	if cache.IsGlobalCacheReady() {
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()

		forumCache := cache.GetGlobalForumCache()
		if err := forumCache.CacheThread(ctx, threadId.String(), thread); err != nil {
			// Логируем ошибку, но не прерываем выполнение
			c.Header("Cache-Warning", "Failed to cache new thread")
		}
	}

	c.JSON(http.StatusOK, gin.H{
		"message": "created thread",
		"thread":  thread,
	})
}
