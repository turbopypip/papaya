package createLike

import (
	"errors"
	"github.com/gin-gonic/gin"
	"github.com/gofrs/uuid"
	"gorm.io/gorm"
	"net/http"
	"papaya-backend/internal/analytics"
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
			"error": "Не удалось прочитать данные лайка",
		})
		return
	}

	// check if LikableType equals "post" or "comment"
	if !likeState.ValidateLikableType(body.LikableType) {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Некорректный тип объекта для лайка",
		})
		return
	}

	// init like id
	likeId, err := uuid.NewV6()
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Не удалось создать идентификатор лайка",
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
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Не удалось загрузить лайки"})
			return
		}

		c.JSON(http.StatusOK, gin.H{
			"message": "Лайк уже поставлен",
			"like":    existing,
			"state":   state,
		})
		return
	}
	if !errors.Is(err, gorm.ErrRecordNotFound) {
		c.JSON(http.StatusInternalServerError, gin.H{"message": "Не удалось проверить лайк"})
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
			"message": "Не удалось поставить лайк",
		})
		return
	}

	state, err := likeState.Load(body.LikableID, body.LikableType, userData.Id)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Не удалось загрузить лайки"})
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
		eventType := analytics.EventPostLiked
		entityType := analytics.EntityPost
		if body.LikableType == models.LikableComment {
			eventType = analytics.EventCommentLiked
			entityType = analytics.EntityComment
		}
		analytics.Record(c.Request.Context(), analytics.Event{
			UserID:     userData.Id,
			EventType:  eventType,
			EntityType: entityType,
			EntityID:   body.LikableID,
			ThreadID:   threadID,
			Metadata: map[string]any{
				"likable_type": body.LikableType,
				"likes_count":  state.Count,
			},
		})
	}

	c.JSON(http.StatusOK, gin.H{
		"message": "Лайк поставлен",
		"like":    like,
		"state":   state,
	})
}
