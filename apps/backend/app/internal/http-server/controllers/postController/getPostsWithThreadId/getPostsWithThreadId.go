package getPostsWithThreadId

import (
	"github.com/gin-gonic/gin"
	"github.com/gofrs/uuid"
	"net/http"
	"papaya-backend/internal/storage"
	"papaya-backend/internal/storage/models"
	"strconv"
)

func GetPostsWithThreadId(c *gin.Context) {
	// Get threadID, page and limit from query params
	threadIDParam := c.Query("thread_id")
	pageParam := c.Query("page")
	limitParam := c.Query("limit")

	// Convert threadIDParam to uuid
	threadID, err := uuid.FromString(threadIDParam)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid thread id"})
		return
	}

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

	// Offset is the post that begins page which will be sent to user
	offset := (page - 1) * limit
	var posts []models.Post

	err = storage.DB.Limit(limit).
		Offset(offset).
		Where("thread_id = ?", threadID).
		Find(&posts).
		Error
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Filed to retrieve posts"})
	}

	// Send data
	c.JSON(http.StatusOK, gin.H{"posts": posts})
}
