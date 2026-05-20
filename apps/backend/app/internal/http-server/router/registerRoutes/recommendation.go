package registerRoutes

import (
	"papaya-backend/internal/http-server/controllers/recommendationController"
	"papaya-backend/internal/http-server/rbac"

	"github.com/gin-gonic/gin"
)

func Recommendation(group *gin.RouterGroup) {
	group.GET("/threads", rbac.Require(rbac.ResourceThreads, rbac.ActionRead), recommendationController.Impl{}.GetThreadRecommendations)
}
