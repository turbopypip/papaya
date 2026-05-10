package userController

import (
	"github.com/gin-gonic/gin"
	"papaya-backend/internal/http-server/controllers/userController/getUser"
)

// UserController defines methods for managing users
type UserController interface {
	GetUser(c *gin.Context)
}

type Impl struct{}

func (r Impl) GetUser(c *gin.Context) {
	getUser.GetUser(c)
}
