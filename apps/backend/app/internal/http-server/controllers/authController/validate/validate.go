package validate

import (
	"github.com/gin-gonic/gin"
	"net/http"
)

func Validate(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"message": "I'm logged in",
	})
}
