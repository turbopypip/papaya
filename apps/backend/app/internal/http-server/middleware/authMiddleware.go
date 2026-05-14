package middleware

import (
	"fmt"
	"github.com/gin-gonic/gin"
	"github.com/golang-jwt/jwt/v5"
	"net/http"
	"os"
	serverAuth "papaya-backend/internal/http-server/auth"
	"papaya-backend/internal/storage"
	"papaya-backend/internal/storage/models"
	"time"
)

func abortUnauthorized(c *gin.Context) {
	serverAuth.ClearAuthCookie(c)
	c.AbortWithStatus(http.StatusUnauthorized)
}

func Auth(c *gin.Context) {
	// Get the token
	tokenString, err := c.Cookie("Authorization")
	if err != nil {
		abortUnauthorized(c)
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
		abortUnauthorized(c)
		return
	}

	if claims, ok := token.Claims.(jwt.MapClaims); ok {
		// Check the exp
		expiresAt, ok := claims["exp"].(float64)
		if !ok || float64(time.Now().Unix()) > expiresAt {
			abortUnauthorized(c)
			return
		}

		// Find the user with token sub
		var user models.User
		sub, ok := claims["sub"].(string)
		if !ok {
			abortUnauthorized(c)
			return
		}

		result := storage.DB.Where("id = ?", sub).Limit(1).Find(&user)
		if result.Error != nil || result.RowsAffected == 0 {
			abortUnauthorized(c)
			return
		}

		var role models.Role
		result = storage.DB.Where("id = ?", user.RoleId).Limit(1).Find(&role)
		if result.Error != nil || result.RowsAffected == 0 {
			abortUnauthorized(c)
			return
		}

		// Attach to request
		c.Set("user", user)
		c.Set("role", role)

		// Continue
		c.Next()
	} else {
		abortUnauthorized(c)
		return
	}
}
