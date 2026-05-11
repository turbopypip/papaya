package registerRoutes

import (
	"papaya-backend/internal/http-server/controllers/likeController"

	"github.com/gin-gonic/gin"
)

func Like(group *gin.RouterGroup) {
	group.POST("", likeController.Impl{}.CreateLike)
	group.POST("/batch", likeController.Impl{}.GetLikesBatch)
	group.GET("", likeController.Impl{}.GetLikes)
	group.DELETE("", likeController.Impl{}.DeleteLike)
}
