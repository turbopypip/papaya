package registerRoutes

import (
	"papaya-backend/internal/http-server/controllers/likeController"
	"papaya-backend/internal/http-server/rbac"

	"github.com/gin-gonic/gin"
)

func Like(group *gin.RouterGroup) {
	group.POST("", rbac.Require(rbac.ResourceLikes, rbac.ActionCreate), likeController.Impl{}.CreateLike)
	group.POST("/batch", rbac.Require(rbac.ResourceLikes, rbac.ActionRead), likeController.Impl{}.GetLikesBatch)
	group.GET("", rbac.Require(rbac.ResourceLikes, rbac.ActionRead), likeController.Impl{}.GetLikes)
	group.DELETE("", rbac.RequireAny(rbac.ResourceLikes, rbac.ActionDelete), likeController.Impl{}.DeleteLike)
}
