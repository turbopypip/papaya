package getThreads

import (
	"github.com/gin-gonic/gin"
	"net/http"
	"papaya-backend/internal/attachments"
	"papaya-backend/internal/storage"
	"papaya-backend/internal/storage/models"
	"strconv"
)

func GetThreads(c *gin.Context) {
	// Get page and limit from query params
	pageParam := c.Query("page")
	limitParam := c.Query("limit")

	// Convert values to int
	page, err := strconv.Atoi(pageParam)
	if err != nil || page < 1 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid page number"})
		return
	}

	limit, err := strconv.Atoi(limitParam)
	if err != nil || limit < 1 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid limit number"})
		return
	}

	// Offset - start thread
	offset := (page - 1) * limit
	var threads []models.Thread

	err = storage.DB.Preload("Author").Limit(limit).Offset(offset).Find(&threads).Error
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Filed to retrieve threads"})
		return
	}
	if err := attachments.AttachToThreads(storage.DB, threads); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to retrieve thread attachments"})
		return
	}

	// Send data
	c.JSON(http.StatusOK, gin.H{"threads": threads})
}
