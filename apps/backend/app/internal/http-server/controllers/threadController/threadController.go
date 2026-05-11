package threadController

import (
	"github.com/gin-gonic/gin"
	"papaya-backend/internal/http-server/controllers/threadController/createThread"
	"papaya-backend/internal/http-server/controllers/threadController/getThread"
	"papaya-backend/internal/http-server/controllers/threadController/getThreads"
	"papaya-backend/internal/http-server/controllers/threadController/searchThreads"
)

// ThreadController defines methods for managing roles.
type ThreadController interface {
	// CreateThread saves a new thread
	CreateThread(c *gin.Context)

	// GetThreads returns a list of threads. Requires page and limit as query params
	GetThreads(c *gin.Context)

	// GetThread returns one thread by id.
	GetThread(c *gin.Context)

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

// GetThread returns one thread by id.
func (r Impl) GetThread(c *gin.Context) {
	getThread.GetThread(c)
}

// SearchThreads returns a list of threads. Requires id or title or categories as query params
func (r Impl) SearchThreads(c *gin.Context) {
	searchThreads.SearchThreads(c)
}
