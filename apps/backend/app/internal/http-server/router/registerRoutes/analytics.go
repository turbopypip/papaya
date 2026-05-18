package registerRoutes

import (
	"papaya-backend/internal/http-server/controllers/analyticsController"
	"papaya-backend/internal/http-server/rbac"

	"github.com/gin-gonic/gin"
)

func Analytics(group *gin.RouterGroup) {
	group.POST("/thread/:id/view", rbac.Require(rbac.ResourceThreads, rbac.ActionRead), analyticsController.Impl{}.RecordThreadView)
}
