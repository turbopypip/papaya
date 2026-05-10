package getUser

import (
	"github.com/gin-gonic/gin"
	"net/http"
	"papaya-backend/internal/storage/models"
)

func GetUser(c *gin.Context) {
	user, _ := c.Get("user")
	userData := user.(models.User)

	// Send data
	c.JSON(http.StatusOK, gin.H{"userData": userData})
}
