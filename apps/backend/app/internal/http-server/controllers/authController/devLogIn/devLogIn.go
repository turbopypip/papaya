package devLogIn

import (
	"net/http"
	"papaya-backend/internal/config"
	serverAuth "papaya-backend/internal/http-server/auth"
	"papaya-backend/internal/storage"
	"papaya-backend/internal/storage/models"

	"github.com/gin-gonic/gin"
)

func DevLogIn(c *gin.Context) {
	if !config.IsDev() {
		c.AbortWithStatus(http.StatusNotFound)
		return
	}

	var user models.User
	result := storage.DB.First(&user, "email = ?", storage.DevUserEmail)
	if result.Error != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to get dev user",
		})
		return
	}

	if err := serverAuth.SetAuthCookie(c, user); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"description": "Failed to create a token",
			"error":       err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"message": "Dev user logged in",
	})
}
