package registerRoutes

import (
	"papaya-backend/internal/http-server/controllers/userController"

	"github.com/gin-gonic/gin"
)

func User(group *gin.RouterGroup) {
	group.GET("", userController.Impl{}.GetUser)
}
