package registerRoutes

import (
	"github.com/gin-gonic/gin"
	"vkid-backend/internal/http-server/controllers/authController"
	"vkid-backend/internal/http-server/middleware"
)

func Auth(group *gin.RouterGroup) {
	group.POST("/signup", authController.Impl{}.SignUp)
	group.POST("/login", authController.Impl{}.LogIn)
	group.GET("/validate",
		middleware.Auth,
		authController.Impl{}.Validate)
}
