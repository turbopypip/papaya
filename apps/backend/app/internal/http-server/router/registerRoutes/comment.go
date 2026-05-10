package registerRoutes

import (
	"github.com/gin-gonic/gin"
	"papaya-backend/internal/http-server/controllers/commentController"
)

func Comment(group *gin.RouterGroup) {
	group.POST("", commentController.Impl{}.CreateComment)
	group.GET("", commentController.Impl{}.GetCommentsWithPostId)
}
