package registerRoutes

import (
	"papaya-backend/internal/http-server/controllers/threadController"
	"papaya-backend/internal/http-server/rbac"

	"github.com/gin-gonic/gin"
)

func Thread(group *gin.RouterGroup) {
	group.POST("", rbac.Require(rbac.ResourceThreads, rbac.ActionCreate), threadController.Impl{}.CreateThread)
	group.GET("/all", rbac.Require(rbac.ResourceThreads, rbac.ActionRead), threadController.Impl{}.GetThreads)
	group.GET("/search", rbac.Require(rbac.ResourceThreads, rbac.ActionRead), threadController.Impl{}.SearchThreads)
	group.GET("/:id", rbac.Require(rbac.ResourceThreads, rbac.ActionRead), threadController.Impl{}.GetThread)
	group.PUT("/:id", rbac.RequireAny(rbac.ResourceThreads, rbac.ActionUpdate), threadController.Impl{}.UpdateThread)
	group.DELETE("/:id", rbac.RequireAny(rbac.ResourceThreads, rbac.ActionDelete), threadController.Impl{}.DeleteThread)
}
