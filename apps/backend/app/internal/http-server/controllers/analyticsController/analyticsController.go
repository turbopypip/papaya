package analyticsController

import (
	"github.com/gin-gonic/gin"
	"papaya-backend/internal/http-server/controllers/analyticsController/recordRecommendationEvent"
	"papaya-backend/internal/http-server/controllers/analyticsController/recordThreadView"
)

type AnalyticsController interface {
	RecordThreadView(c *gin.Context)
	RecordRecommendationEvent(c *gin.Context)
}

type Impl struct{}

func (r Impl) RecordThreadView(c *gin.Context) {
	recordThreadView.RecordThreadView(c)
}

func (r Impl) RecordRecommendationEvent(c *gin.Context) {
	recordRecommendationEvent.RecordRecommendationEvent(c)
}
