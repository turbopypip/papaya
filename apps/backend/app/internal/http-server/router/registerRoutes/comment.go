package registerRoutes

import (
	"github.com/gin-gonic/gin"
	"papaya-backend/internal/http-server/controllers/commentController"
	"papaya-backend/internal/http-server/rbac"
)

func Comment(group *gin.RouterGroup) {
	group.POST("", rbac.Require(rbac.ResourceComments, rbac.ActionCreate), commentController.Impl{}.CreateComment)
	group.GET("", rbac.Require(rbac.ResourceComments, rbac.ActionRead), commentController.Impl{}.GetCommentsWithPostId)
	group.PUT("/:id", rbac.RequireAny(rbac.ResourceComments, rbac.ActionUpdate), commentController.Impl{}.UpdateComment)
	group.DELETE("/:id", rbac.RequireAny(rbac.ResourceComments, rbac.ActionDelete), commentController.Impl{}.DeleteComment)
}
