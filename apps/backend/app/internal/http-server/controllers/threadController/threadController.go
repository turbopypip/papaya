package threadController

import (
	"github.com/gin-gonic/gin"
	"vkid-backend/internal/http-server/controllers/threadController/createThread"
	"vkid-backend/internal/http-server/controllers/threadController/getThreads"
	"vkid-backend/internal/http-server/controllers/threadController/searchThreads"
)

// ThreadController defines methods for managing roles.
type ThreadController interface {
	// CreateThread saves a new thread
	CreateThread(c *gin.Context)

	// GetThreads returns a list of threads. Requires page and limit as query params
	GetThreads(c *gin.Context)

	// SearchThreads returns a list of threads. Requires id or title or categories as query params
	SearchThreads(c *gin.Context)
}

type Impl struct{}

// CreateThread saves a new thread
func (r Impl) CreateThread(c *gin.Context) {
	createThread.CreateThread(c)
}

// GetThreads returns a list of threads. Requires page and limit as query params
func (r Impl) GetThreads(c *gin.Context) {
	getThreads.GetThreads(c)
}

// SearchThreads returns a list of threads. Requires id or title or categories as query params
func (r Impl) SearchThreads(c *gin.Context) {
	searchThreads.SearchThreads(c)
}
