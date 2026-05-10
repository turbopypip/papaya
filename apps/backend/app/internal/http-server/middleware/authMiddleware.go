package middleware

import (
	"fmt"
	"github.com/gin-gonic/gin"
	"github.com/golang-jwt/jwt/v5"
	"net/http"
	"os"
	"papaya-backend/internal/storage"
	"papaya-backend/internal/storage/models"
	"time"
)

func Auth(c *gin.Context) {
	// Get the token
	tokenString, err := c.Cookie("Authorization")
	if err != nil {
		c.AbortWithStatus(http.StatusUnauthorized)
		return
	}

	// Decode
	token, err := jwt.Parse(tokenString, func(token *jwt.Token) (interface{}, error) {
		if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
			return nil, fmt.Errorf("unexpected signing method: %v", token.Header["alg"])
		}

		return []byte(os.Getenv("SECRET")), nil
	})
	if err != nil {
		c.AbortWithStatus(http.StatusUnauthorized)
		return
	}

	if claims, ok := token.Claims.(jwt.MapClaims); ok {
		// Check the exp
		expiresAt, ok := claims["exp"].(float64)
		if !ok || float64(time.Now().Unix()) > expiresAt {
			c.AbortWithStatus(http.StatusUnauthorized)
			return
		}

		// Find the user with token sub
		var user models.User
		sub, ok := claims["sub"].(string)
		if !ok {
			c.AbortWithStatus(http.StatusUnauthorized)
			return
		}

		storage.DB.First(&user, "id = ?", sub)
		if user.Username == "" {
			c.AbortWithStatus(http.StatusUnauthorized)
			return
		}

		// Attach to request
		c.Set("user", user)

		// Continue
		c.Next()
	} else {
		c.AbortWithStatus(http.StatusUnauthorized)
		return
	}
}
