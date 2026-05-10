package deleteLike

import (
	"github.com/gin-gonic/gin"
	"github.com/gofrs/uuid"
	"net/http"
	"papaya-backend/internal/storage"
	"papaya-backend/internal/storage/models"
)

func DeleteLike(c *gin.Context) {
	var body struct {
		LikableID   uuid.UUID `json:"likable_id"`
		LikableType string    `json:"likable_type"`
	}

	if err := c.ShouldBindJSON(&body); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request body", "details": err.Error()})
		return
	}

	if body.LikableType != models.LikablePost && body.LikableType != models.LikableComment {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid likable type"})
		return
	}

	user, _ := c.Get("user")
	userData := user.(models.User)

	result := storage.DB.
		Where("user_id = ? AND likable_id = ? AND likable_type = ?", userData.Id, body.LikableID, body.LikableType).
		Delete(&models.Like{})

	if result.Error != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to delete like"})
		return
	}

	if result.RowsAffected == 0 {
		c.JSON(http.StatusNotFound, gin.H{"message": "Like not found"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "Like deleted"})
}
