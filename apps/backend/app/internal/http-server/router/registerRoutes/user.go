package registerRoutes

import (
	"papaya-backend/internal/http-server/controllers/userController"
	"papaya-backend/internal/http-server/rbac"

	"github.com/gin-gonic/gin"
)

func User(group *gin.RouterGroup) {
	group.GET("", rbac.Require(rbac.ResourceUsers, rbac.ActionRead), userController.Impl{}.GetUser)
}
