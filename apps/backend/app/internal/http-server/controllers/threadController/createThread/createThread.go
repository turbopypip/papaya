package createThread

import (
	"context"
	"net/http"
	"papaya-backend/internal/attachments"
	"papaya-backend/internal/cache"
	"papaya-backend/internal/forumvalidation"
	"papaya-backend/internal/http-server/rbac"
	"papaya-backend/internal/storage"
	"papaya-backend/internal/storage/models"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/gofrs/uuid"
	"gorm.io/gorm"
)

func CreateThread(c *gin.Context) {
	var body struct {
		Title      string   `json:"title"`
		Categories []string `json:"categories"`
	}

	if strings.HasPrefix(c.GetHeader("Content-Type"), "multipart/form-data") {
		body.Title = c.PostForm("title")
		body.Categories = c.PostFormArray("categories")
	} else if err := c.ShouldBindJSON(&body); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error":   "Failed to get body",
			"details": err.Error(),
		})
		return
	}
	categories, err := forumvalidation.ValidateThread(body.Title, body.Categories)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	body.Title = strings.TrimSpace(body.Title)
	body.Categories = categories
	if len(body.Categories) > 0 && !rbac.CanAny(c, rbac.ResourceCategories, rbac.ActionCreate) {
		c.JSON(http.StatusForbidden, gin.H{"error": "You cannot add categories"})
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

	var savedFiles []string
	err = storage.DB.Transaction(func(tx *gorm.DB) error {
		if err := tx.Create(&thread).Error; err != nil {
			return err
		}

		createdAttachments, paths, err := attachments.CreateFromRequest(
			c,
			tx,
			attachments.OwnerTypeThread,
			thread.Id,
			userData.Id,
		)
		savedFiles = append(savedFiles, paths...)
		if err != nil {
			return err
		}

		thread.Attachments = createdAttachments
		return nil
	})
	if err != nil {
		attachments.CleanupFiles(savedFiles)
		if attachments.IsValidationError(err) {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}
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
