package registerRoutes

import (
	"github.com/gin-gonic/gin"
	"vkid-backend/internal/http-server/controllers/testController"
)

func Test(api *gin.RouterGroup) {
	api.GET("/ping", testController.Impl{}.Ping)
}
