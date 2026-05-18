package getLikes

import (
	"net/http"
	"papaya-backend/internal/http-server/controllers/likeController/likeState"

	"github.com/gin-gonic/gin"
	"github.com/gofrs/uuid"
)

type batchRequest struct {
	Likables []struct {
		ID   string `json:"likable_id"`
		Type string `json:"likable_type"`
	} `json:"likables"`
}

func GetLikes(c *gin.Context) {
	likableIDParam := c.Query("likable_id")
	likableType := c.Query("likable_type")

	if likableIDParam == "" || likableType == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Укажите идентификатор и тип объекта для лайка"})
		return
	}

	state, ok := loadStateFromParams(c, likableIDParam, likableType)
	if !ok {
		return
	}

	c.JSON(http.StatusOK, state)
}

func GetLikesBatch(c *gin.Context) {
	userData, ok := likeState.CurrentUser(c)
	if !ok {
		return
	}

	var body batchRequest
	if err := c.ShouldBindJSON(&body); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Некорректный формат запроса"})
		return
	}

	results := make([]likeState.Result, 0, len(body.Likables))
	for _, likable := range body.Likables {
		if likable.ID == "" || likable.Type == "" {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Укажите идентификатор и тип объекта для лайка"})
			return
		}

		if !likeState.ValidateLikableType(likable.Type) {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Некорректный тип объекта для лайка"})
			return
		}

		likableID, err := uuid.FromString(likable.ID)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Некорректный идентификатор объекта для лайка"})
			return
		}

		state, err := likeState.Load(likableID, likable.Type, userData.Id)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Не удалось загрузить лайки"})
			return
		}

		results = append(results, state)
	}

	c.JSON(http.StatusOK, gin.H{"results": results})
}

func loadStateFromParams(c *gin.Context, likableIDParam, likableType string) (likeState.Result, bool) {
	userData, ok := likeState.CurrentUser(c)
	if !ok {
		return likeState.Result{}, false
	}

	if !likeState.ValidateLikableType(likableType) {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Некорректный тип объекта для лайка"})
		return likeState.Result{}, false
	}

	likableID, err := uuid.FromString(likableIDParam)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Некорректный идентификатор объекта для лайка"})
		return likeState.Result{}, false
	}

	state, err := likeState.Load(likableID, likableType, userData.Id)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Не удалось загрузить лайки"})
		return likeState.Result{}, false
	}

	return state, true
}
