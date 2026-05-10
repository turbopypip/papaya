package createLike

import (
	"github.com/gin-gonic/gin"
	"github.com/gofrs/uuid"
	"net/http"
	"papaya-backend/internal/storage"
	"papaya-backend/internal/storage/models"
)

func CreateLike(c *gin.Context) {
	var body struct {
		LikableID   uuid.UUID `json:"likable_id"`
		LikableType string    `json:"likable_type"`
	}

	// check if body exists
	if err := c.ShouldBindJSON(&body); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error":   "Failed to get body",
			"details": err.Error(),
		})
		return
	}

	// check if LikableType equals "post" or "comment"
	if body.LikableType != models.LikablePost && body.LikableType != models.LikableComment {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Invalid likable type",
		})
		return
	}

	// init like id
	likeId, err := uuid.NewV6()
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

	// init Comment
	like := models.Like{
		Id:          likeId,
		UserId:      userData.Id,
		LikableID:   body.LikableID,
		LikableType: body.LikableType,
	}

	// save Comment
	result := storage.DB.Create(&like)
	if result.Error != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"message": "Failed to create comment",
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"message": "created like",
		"like":    like,
	})
}
