package searchThreads

import (
	"github.com/gin-gonic/gin"
	"github.com/gofrs/uuid"
	"github.com/lib/pq"
	"net/http"
	"vkid-backend/internal/storage"
	"vkid-backend/internal/storage/models"
)

func SearchThreads(c *gin.Context) {
	// Get title, id from query params
	title := c.Query("title")
	idParam := c.Query("id")
	categories := pq.StringArray(c.QueryArray("categories")) // string array

	if title == "" && idParam == "" && len(categories) == 0 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "expected 1 or more args. 0 given"})
		return
	}

	// Init a query with thread model
	query := storage.DB.Model(&models.Thread{})

	// Building a query
	if title != "" {
		const similarityThreshold = 0.3
		query = query.Where("similarity(title, ?) > ?",
			title,
			similarityThreshold) // ILIKE for insensibility to text case
	}

	if idParam != "" {
		id, err := uuid.FromString(idParam)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid ID format"})
			return
		}
		query = query.Where("id = ?", id)
	}

	if len(categories) > 0 {
		query = query.Where("categories && ?", categories)
	}

	// Search threads
	var threads []models.Thread
	if err := query.Find(&threads).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to search threads"})
		return
	}

	// Send data
	c.JSON(http.StatusOK, gin.H{"threads": threads})
}
