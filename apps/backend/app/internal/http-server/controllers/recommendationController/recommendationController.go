package recommendationController

import (
	"github.com/gin-gonic/gin"
	"papaya-backend/internal/http-server/controllers/recommendationController/getThreadRecommendations"
)

type RecommendationController interface {
	GetThreadRecommendations(c *gin.Context)
}

type Impl struct{}

func (r Impl) GetThreadRecommendations(c *gin.Context) {
	getThreadRecommendations.GetThreadRecommendations(c)
}
