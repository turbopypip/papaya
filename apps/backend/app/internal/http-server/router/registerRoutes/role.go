package registerRoutes

import (
	"github.com/gin-gonic/gin"
	"papaya-backend/internal/http-server/controllers/roleController"
)

func Role(group *gin.RouterGroup) {
	group.POST("", roleController.Impl{}.CreateRole)
}
