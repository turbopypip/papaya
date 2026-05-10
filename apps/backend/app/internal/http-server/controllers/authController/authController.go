// TODO: add errors descriptions

package authController

import (
	"github.com/gin-gonic/gin"
	"vkid-backend/internal/http-server/controllers/authController/logIn"
	"vkid-backend/internal/http-server/controllers/authController/signUp"
	"vkid-backend/internal/http-server/controllers/authController/validate"
)

// AuthController defines methods for managing auth
type AuthController interface {
	// SignUp adds a new user to the database
	SignUp(c *gin.Context)

	// LogIn returns an auth token to user
	LogIn(c *gin.Context)

	// Validate returns a log in message
	Validate(c *gin.Context)
}

type Impl struct{}

// SignUp adds a new user to the database
func (r Impl) SignUp(c *gin.Context) {
	signUp.SignUp(c)
}

// LogIn returns an auth token to user
func (r Impl) LogIn(c *gin.Context) {
	logIn.LogIn(c)
}

func (r Impl) Validate(c *gin.Context) {
	validate.Validate(c)
}
