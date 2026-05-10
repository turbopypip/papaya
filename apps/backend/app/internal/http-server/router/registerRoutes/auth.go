package registerRoutes

import (
	"github.com/gin-gonic/gin"
	"papaya-backend/internal/http-server/controllers/authController"
	"papaya-backend/internal/http-server/middleware"
)

func Auth(group *gin.RouterGroup) {
	group.POST("/signup", authController.Impl{}.SignUp)
	group.POST("/login", authController.Impl{}.LogIn)
	group.GET("/validate",
		middleware.Auth,
		authController.Impl{}.Validate)
}
