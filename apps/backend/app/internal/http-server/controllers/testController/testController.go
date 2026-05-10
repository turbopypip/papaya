package testController

import (
	"github.com/gin-gonic/gin"
	"papaya-backend/internal/http-server/controllers/testController/ping"
)

// TestController defines methods for testing api
type TestController interface {
	// Ping test connection to api
	Ping(c *gin.Context)
}

type Impl struct{}

// Ping test connection to api
func (r Impl) Ping(c *gin.Context) {
	ping.Ping(c)
}
