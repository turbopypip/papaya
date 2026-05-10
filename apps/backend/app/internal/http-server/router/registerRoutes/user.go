package registerRoutes

import (
	"time"
	"vkid-backend/internal/cache"
	"vkid-backend/internal/http-server/controllers/userController"

	"github.com/gin-gonic/gin"
)

func User(group *gin.RouterGroup) {
	// GET запросы с кэшированием
	group.GET("",
		cache.SafeCacheMiddleware(15*time.Second),
		userController.Impl{}.GetUser,
	)
}
