package registerRoutes

import (
	"papaya-backend/internal/http-server/controllers/threadController"

	"github.com/gin-gonic/gin"
)

func Thread(group *gin.RouterGroup) {
	group.POST("", threadController.Impl{}.CreateThread)
	group.GET("/all", threadController.Impl{}.GetThreads)
	group.GET("/search", threadController.Impl{}.SearchThreads)
	group.GET("/:id", threadController.Impl{}.GetThread)
}
