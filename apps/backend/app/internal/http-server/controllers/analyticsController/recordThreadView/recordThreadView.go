package recordThreadView

import (
	"errors"
	"net/http"
	"papaya-backend/internal/analytics"
	"papaya-backend/internal/storage"
	"papaya-backend/internal/storage/models"

	"github.com/gin-gonic/gin"
	"github.com/gofrs/uuid"
	"gorm.io/gorm"
)

func RecordThreadView(c *gin.Context) {
	threadID, err := uuid.FromString(c.Param("id"))
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

	user, ok := c.Get("user")
	if !ok {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "Войдите в аккаунт"})
		return
	}

	userData, ok := user.(models.User)
	if !ok {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "Войдите в аккаунт"})
		return
	}

	analytics.Record(c.Request.Context(), analytics.Event{
		UserID:     userData.Id,
		EventType:  analytics.EventThreadViewed,
		EntityType: analytics.EntityThread,
		EntityID:   thread.Id,
		ThreadID:   thread.Id,
		Metadata: map[string]any{
			"source": "thread_page",
		},
	})

	c.JSON(http.StatusOK, gin.H{"message": "Просмотр треда записан"})
}
