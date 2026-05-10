package registerRoutes

import (
	"papaya-backend/internal/cache"
	"papaya-backend/internal/http-server/controllers/likeController"
	"time"

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
