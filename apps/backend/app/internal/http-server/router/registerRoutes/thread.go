package registerRoutes

import (
	"papaya-backend/internal/cache"
	"papaya-backend/internal/http-server/controllers/threadController"
	"time"

	"github.com/gin-gonic/gin"
)

func Thread(group *gin.RouterGroup) {
	group.POST("", threadController.Impl{}.CreateThread)

	// GET запросы с кэшированием
	group.GET("/all",
		cache.SafeCacheMiddleware(15*time.Second),
		threadController.Impl{}.GetThreads,
	)
	group.GET("/search",
		cache.SafeCacheMiddleware(15*time.Second),
		threadController.Impl{}.SearchThreads,
	)
}
