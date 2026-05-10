package registerRoutes

import (
	"papaya-backend/internal/cache"
	"papaya-backend/internal/http-server/controllers/userController"
	"time"

	"github.com/gin-gonic/gin"
)

func User(group *gin.RouterGroup) {
	// GET запросы с кэшированием
	group.GET("",
		cache.SafeCacheMiddleware(15*time.Second),
		userController.Impl{}.GetUser,
	)
}
