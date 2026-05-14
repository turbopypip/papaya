package registerRoutes

import (
	"github.com/gin-gonic/gin"
	"papaya-backend/internal/http-server/controllers/roleController"
	"papaya-backend/internal/http-server/rbac"
)

func Role(group *gin.RouterGroup) {
	group.POST("", rbac.RequireAdmin(), roleController.Impl{}.CreateRole)
}
