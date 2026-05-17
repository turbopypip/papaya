package getCommentsWithPostId

import (
	"github.com/gin-gonic/gin"
	"github.com/gofrs/uuid"
	"net/http"
	"papaya-backend/internal/attachments"
	"papaya-backend/internal/storage"
	"papaya-backend/internal/storage/models"
	"strconv"
)

func GetCommentsByPostId(c *gin.Context) {
	// Get postID, page and limit from query params
	postIDParam := c.Query("post_id")
	pageParam := c.Query("page")
	limitParam := c.Query("limit")

	// Convert postIDParam to uuid
	postID, err := uuid.FromString(postIDParam)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid post id"})
		return
	}

	// Convert page and limit to int
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
	var comments []models.Comment

	err = storage.DB.Preload("Author").
		Limit(limit).
		Offset(offset).
		Where("post_id = ?", postID).
		Find(&comments).
		Error
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Filed to retrieve posts"})
		return
	}
	if err := attachments.AttachToComments(storage.DB, comments); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to retrieve comment attachments"})
		return
	}

	// Send data
	c.JSON(http.StatusOK, gin.H{"comments": comments})
}
