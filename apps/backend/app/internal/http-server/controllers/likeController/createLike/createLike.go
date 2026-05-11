package createLike

import (
	"errors"
	"github.com/gin-gonic/gin"
	"github.com/gofrs/uuid"
	"gorm.io/gorm"
	"net/http"
	"papaya-backend/internal/http-server/controllers/likeController/likeState"
	"papaya-backend/internal/realtime"
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
	if !likeState.ValidateLikableType(body.LikableType) {
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
	userData, ok := likeState.CurrentUser(c)
	if !ok {
		return
	}

	var existing models.Like
	err = storage.DB.
		Where("user_id = ? AND likable_id = ? AND likable_type = ?", userData.Id, body.LikableID, body.LikableType).
		First(&existing).Error
	if err == nil {
		state, loadErr := likeState.Load(body.LikableID, body.LikableType, userData.Id)
		if loadErr != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to load likes"})
			return
		}

		c.JSON(http.StatusOK, gin.H{
			"message": "already liked",
			"like":    existing,
			"state":   state,
		})
		return
	}
	if !errors.Is(err, gorm.ErrRecordNotFound) {
		c.JSON(http.StatusInternalServerError, gin.H{"message": "Failed to check like"})
		return
	}

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
			"message": "Failed to create like",
		})
		return
	}

	state, err := likeState.Load(body.LikableID, body.LikableType, userData.Id)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to load likes"})
		return
	}

	if threadID, ok, err := likeState.ResolveThreadID(body.LikableID, body.LikableType); err == nil && ok {
		realtime.DefaultHub.Publish(threadID.String(), realtime.Event{
			Type:        realtime.EventLikeCreated,
			ThreadID:    threadID.String(),
			LikableType: body.LikableType,
			LikableID:   body.LikableID.String(),
			Count:       state.Count,
		})
	}

	c.JSON(http.StatusOK, gin.H{
		"message": "created like",
		"like":    like,
		"state":   state,
	})
}
