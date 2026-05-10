package registerRoutes

import (
	"github.com/gin-gonic/gin"
	"vkid-backend/internal/http-server/controllers/attachementController"
	"vkid-backend/internal/http-server/middleware"
)

func AttachmentRoutes(router *gin.Engine, baseUrl string) {
	router.POST(baseUrl+"/attachment",
		middleware.Auth,
		attachementController.Impl{}.CreateAttachment)
}
