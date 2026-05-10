package registerRoutes

import (
	"github.com/gin-gonic/gin"
	"vkid-backend/internal/http-server/controllers/roleController"
)

func Role(group *gin.RouterGroup) {
	group.POST("", roleController.Impl{}.CreateRole)
}
