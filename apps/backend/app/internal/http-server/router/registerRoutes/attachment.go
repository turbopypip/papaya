package registerRoutes

import (
	"github.com/gin-gonic/gin"
	"papaya-backend/internal/http-server/controllers/attachementController"
	"papaya-backend/internal/http-server/middleware"
	"papaya-backend/internal/http-server/rbac"
)

func AttachmentRoutes(router *gin.Engine, baseUrl string) {
	router.POST(baseUrl+"/attachment",
		middleware.Auth,
		rbac.Require(rbac.ResourceAttachments, rbac.ActionCreate),
		attachementController.Impl{}.CreateAttachment)
}
