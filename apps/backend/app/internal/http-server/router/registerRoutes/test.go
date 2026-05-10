package registerRoutes

import (
	"github.com/gin-gonic/gin"
	"papaya-backend/internal/http-server/controllers/testController"
)

func Test(api *gin.RouterGroup) {
	api.GET("/ping", testController.Impl{}.Ping)
}
