package recordRecommendationEvent

import (
	"errors"
	"net/http"
	"papaya-backend/internal/analytics"
	"papaya-backend/internal/http-server/rbac"
	"papaya-backend/internal/storage"
	"papaya-backend/internal/storage/models"
	"strings"

	"github.com/gin-gonic/gin"
	"github.com/gofrs/uuid"
	"gorm.io/gorm"
)

type recommendationEventRequest struct {
	EventType            string `json:"event_type"`
	ThreadID             string `json:"thread_id"`
	ModelVersion         string `json:"model_version"`
	Position             int    `json:"position"`
	RecommendationSource string `json:"recommendation_source"`
	Placement            string `json:"placement"`
	RunID                string `json:"run_id"`
	GenerationID         string `json:"generation_id"`
}

func RecordRecommendationEvent(c *gin.Context) {
	var payload recommendationEventRequest
	if err := c.ShouldBindJSON(&payload); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Некорректный формат события"})
		return
	}

	eventType := strings.TrimSpace(payload.EventType)
	if eventType != analytics.EventRecommendationImpression && eventType != analytics.EventRecommendationClicked {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Некорректный тип события рекомендации"})
		return
	}

	threadID, err := uuid.FromString(payload.ThreadID)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Некорректный идентификатор треда"})
		return
	}

	var thread models.Thread
	err = storage.DB.First(&thread, "id = ?", threadID).Error
	if errors.Is(err, gorm.ErrRecordNotFound) {
		c.JSON(http.StatusNotFound, gin.H{"error": "Тред не найден"})
		return
	}
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Не удалось проверить тред"})
		return
	}

	user, ok := rbac.CurrentUser(c)
	if !ok {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "Войдите в аккаунт"})
		return
	}

	recommendationSource := strings.TrimSpace(payload.RecommendationSource)
	if recommendationSource == "" {
		recommendationSource = "model"
	}
	placement := strings.TrimSpace(payload.Placement)
	if placement == "" {
		placement = "unknown"
	}

	analytics.Record(c.Request.Context(), analytics.Event{
		UserID:     user.Id,
		EventType:  eventType,
		EntityType: analytics.EntityRecommendation,
		EntityID:   thread.Id,
		ThreadID:   thread.Id,
		Metadata: map[string]any{
			"model_version":         payload.ModelVersion,
			"position":              payload.Position,
			"recommendation_source": recommendationSource,
			"placement":             placement,
			"run_id":                payload.RunID,
			"generation_id":         payload.GenerationID,
		},
	})

	c.JSON(http.StatusOK, gin.H{"message": "Событие рекомендации записано"})
}
