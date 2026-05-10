package registerRoutes

import (
	"time"
	"vkid-backend/internal/cache"
	"vkid-backend/internal/http-server/controllers/postController"

	"github.com/gin-gonic/gin"
)

func Post(group *gin.RouterGroup) {
	group.POST("", postController.Impl{}.CreatePost)

	// GET запросы с кэшированием
	group.GET("",
		cache.SafeCacheMiddleware(15*time.Second),
		postController.Impl{}.GetPostsWithThreadId,
	)
}
