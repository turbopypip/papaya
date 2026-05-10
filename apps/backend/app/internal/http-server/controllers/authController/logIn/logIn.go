package logIn

import (
	"github.com/gin-gonic/gin"
	"github.com/golang-jwt/jwt/v5"
	"golang.org/x/crypto/bcrypt"
	"net/http"
	"os"
	"time"
	"vkid-backend/internal/storage"
	"vkid-backend/internal/storage/models"
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

	token := jwt.NewWithClaims(jwt.SigningMethodHS256, jwt.MapClaims{
		"sub": user.Id,
		"exp": time.Now().Add(time.Hour * 24 * 30).Unix(),
	})

	// Sign and get the complete encoded token as a string using the secret
	tokenString, err := token.SignedString([]byte(os.Getenv("SECRET")))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"description": "Failed to create a token",
			"error":       err.Error(),
		})

		return
	}

	c.SetSameSite(http.SameSiteLaxMode)
	c.SetCookie("Authorization",
		tokenString,
		3600*24*30,
		"",
		"",
		false,
		true)

	c.JSON(http.StatusOK, gin.H{})
}
