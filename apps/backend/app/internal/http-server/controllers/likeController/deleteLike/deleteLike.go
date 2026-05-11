package deleteLike

import (
	"github.com/gin-gonic/gin"
	"github.com/gofrs/uuid"
	"net/http"
	"papaya-backend/internal/http-server/controllers/likeController/likeState"
	"papaya-backend/internal/realtime"
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

	if !likeState.ValidateLikableType(body.LikableType) {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid likable type"})
		return
	}

	userData, ok := likeState.CurrentUser(c)
	if !ok {
		return
	}

	result := storage.DB.
		Where("user_id = ? AND likable_id = ? AND likable_type = ?", userData.Id, body.LikableID, body.LikableType).
		Unscoped().
		Delete(&models.Like{})

	if result.Error != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to delete like"})
		return
	}

	state, err := likeState.Load(body.LikableID, body.LikableType, userData.Id)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to load likes"})
		return
	}

	message := "Like deleted"
	if result.RowsAffected == 0 {
		message = "Like not found"
	} else if threadID, ok, err := likeState.ResolveThreadID(body.LikableID, body.LikableType); err == nil && ok {
		realtime.DefaultHub.Publish(threadID.String(), realtime.Event{
			Type:        realtime.EventLikeDeleted,
			ThreadID:    threadID.String(),
			LikableType: body.LikableType,
			LikableID:   body.LikableID.String(),
			Count:       state.Count,
		})
	}

	c.JSON(http.StatusOK, gin.H{"message": message, "state": state})
}
