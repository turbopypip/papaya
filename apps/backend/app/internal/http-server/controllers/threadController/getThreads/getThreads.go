package getThreads

import (
	"github.com/gin-gonic/gin"
	"net/http"
	"strconv"
	"vkid-backend/internal/storage"
	"vkid-backend/internal/storage/models"
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

	err = storage.DB.Limit(limit).Offset(offset).Find(&threads).Error
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Filed to retrieve threads"})
	}

	// Send data
	c.JSON(http.StatusOK, gin.H{"threads": threads})
}
