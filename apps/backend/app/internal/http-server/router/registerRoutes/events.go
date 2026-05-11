package registerRoutes

import (
	"papaya-backend/internal/http-server/controllers/eventController"

	"github.com/gin-gonic/gin"
)

func Events(group *gin.RouterGroup) {
	group.GET("/thread/:threadId", eventController.Impl{}.SubscribeThread)
}
