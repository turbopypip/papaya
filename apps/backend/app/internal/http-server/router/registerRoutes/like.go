package registerRoutes

import (
	"time"
	"vkid-backend/internal/cache"
	"vkid-backend/internal/http-server/controllers/likeController"

	"github.com/gin-gonic/gin"
)

func Like(group *gin.RouterGroup) {
	group.POST("", likeController.Impl{}.CreateLike)
	group.GET("",
		cache.SafeCacheMiddleware(15*time.Second),
		likeController.Impl{}.GetLikes,
	)
	group.DELETE("", likeController.Impl{}.DeleteLike)
}
