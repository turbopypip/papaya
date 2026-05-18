package registerRoutes

import (
	"papaya-backend/internal/http-server/controllers/postController"
	"papaya-backend/internal/http-server/rbac"

	"github.com/gin-gonic/gin"
)

func Post(group *gin.RouterGroup) {
	group.POST("", rbac.Require(rbac.ResourcePosts, rbac.ActionCreate), postController.Impl{}.CreatePost)
	group.GET("/search", rbac.Require(rbac.ResourcePosts, rbac.ActionRead), postController.Impl{}.SearchPosts)
	group.GET("", rbac.Require(rbac.ResourcePosts, rbac.ActionRead), postController.Impl{}.GetPostsWithThreadId)
	group.PUT("/:id", rbac.RequireAny(rbac.ResourcePosts, rbac.ActionUpdate), postController.Impl{}.UpdatePost)
	group.DELETE("/:id", rbac.RequireAny(rbac.ResourcePosts, rbac.ActionDelete), postController.Impl{}.DeletePost)
}
