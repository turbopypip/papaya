package searchPosts

import (
	"net/http"
	"strconv"
	"strings"

	"github.com/gin-gonic/gin"
	"github.com/gofrs/uuid"

	"papaya-backend/internal/attachments"
	"papaya-backend/internal/storage"
	"papaya-backend/internal/storage/models"
)

func SearchPosts(c *gin.Context) {
	threadIDParam := c.Query("thread_id")
	queryParam := strings.TrimSpace(c.Query("query"))
	pageParam := c.DefaultQuery("page", "1")
	limitParam := c.DefaultQuery("limit", "100")

	threadID, err := uuid.FromString(threadIDParam)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Некорректный идентификатор треда"})
		return
	}

	if queryParam == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Введите поисковый запрос"})
		return
	}

	page, err := strconv.Atoi(pageParam)
	if err != nil || page < 1 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Некорректный номер страницы"})
		return
	}

	limit, err := strconv.Atoi(limitParam)
	if err != nil || limit < 1 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Некорректный лимит"})
		return
	}

	offset := (page - 1) * limit
	var posts []models.Post

	err = storage.DB.Preload("Author").
		Limit(limit).
		Offset(offset).
		Where("thread_id = ? AND content ILIKE ?", threadID, "%"+queryParam+"%").
		Find(&posts).
		Error
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Не удалось найти посты"})
		return
	}
	if err := attachments.AttachToPosts(storage.DB, posts); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Не удалось получить вложения постов"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"posts": posts})
}
