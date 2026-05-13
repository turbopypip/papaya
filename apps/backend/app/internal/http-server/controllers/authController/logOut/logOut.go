package logOut

import (
	"net/http"
	serverAuth "papaya-backend/internal/http-server/auth"

	"github.com/gin-gonic/gin"
)

func LogOut(c *gin.Context) {
	serverAuth.ClearAuthCookie(c)
	c.JSON(http.StatusOK, gin.H{
		"message": "Logged out",
	})
}
