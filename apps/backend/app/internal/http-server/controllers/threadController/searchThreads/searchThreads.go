package searchThreads

import (
	"github.com/gin-gonic/gin"
	"github.com/gofrs/uuid"
	"github.com/lib/pq"
	"net/http"
	"papaya-backend/internal/attachments"
	"papaya-backend/internal/storage"
	"papaya-backend/internal/storage/models"
	"strconv"
)

func SearchThreads(c *gin.Context) {
	// Get title, id from query params
	title := c.Query("title")
	idParam := c.Query("id")
	categories := pq.StringArray(c.QueryArray("categories")) // string array
	pageParam := c.DefaultQuery("page", "1")
	limitParam := c.DefaultQuery("limit", "10")

	if title == "" && idParam == "" && len(categories) == 0 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Укажите хотя бы один параметр поиска"})
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

	// Init a query with thread model
	query := storage.DB.Model(&models.Thread{})

	// Building a query
	if title != "" {
		const similarityThreshold = 0.3
		query = query.Where("title ILIKE ? OR similarity(title, ?) > ?",
			"%"+title+"%",
			title,
			similarityThreshold) // ILIKE for insensibility to text case
	}

	if idParam != "" {
		id, err := uuid.FromString(idParam)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Некорректный идентификатор"})
			return
		}
		query = query.Where("id = ?", id)
	}

	if len(categories) > 0 {
		query = query.Where("categories && ?", categories)
	}

	// Search threads
	var total int64
	if err := query.Count(&total).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Не удалось посчитать треды"})
		return
	}

	offset := (page - 1) * limit
	var threads []models.Thread
	if err := query.Preload("Author").Limit(limit).Offset(offset).Find(&threads).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Не удалось найти треды"})
		return
	}
	if err := attachments.AttachToThreads(storage.DB, threads); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Не удалось получить вложения тредов"})
		return
	}

	// Send data
	c.JSON(http.StatusOK, gin.H{
		"threads": threads,
		"page":    page,
		"limit":   limit,
		"total":   total,
	})
}
