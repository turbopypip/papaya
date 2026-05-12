package registerRoutes

import (
	"papaya-backend/internal/http-server/controllers/postController"

	"github.com/gin-gonic/gin"
)

func Post(group *gin.RouterGroup) {
	group.POST("", postController.Impl{}.CreatePost)
	group.GET("", postController.Impl{}.GetPostsWithThreadId)
	group.PUT("/:id", postController.Impl{}.UpdatePost)
	group.DELETE("/:id", postController.Impl{}.DeletePost)
}
