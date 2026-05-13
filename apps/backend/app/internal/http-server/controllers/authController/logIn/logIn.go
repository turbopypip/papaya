package logIn

import (
	"github.com/gin-gonic/gin"
	"golang.org/x/crypto/bcrypt"
	"net/http"
	serverAuth "papaya-backend/internal/http-server/auth"
	"papaya-backend/internal/storage"
	"papaya-backend/internal/storage/models"
)

func LogIn(c *gin.Context) {

	// Get email, password off req body
	var body struct {
		Email    string `json:"email"`
		Password string `json:"password"`
	}

	if err := c.ShouldBindJSON(&body); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"description": "Failed to get body",
			"error":       err.Error(),
		})
		return
	}

	var user models.User
	storage.DB.First(&user, "email = ?", body.Email)
	if user.Username == "" {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Failed to get user",
		})

		return
	}

	err := bcrypt.CompareHashAndPassword([]byte(user.PasswordHash), []byte(body.Password))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Invalid email or password",
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

	c.JSON(http.StatusOK, gin.H{})
}
