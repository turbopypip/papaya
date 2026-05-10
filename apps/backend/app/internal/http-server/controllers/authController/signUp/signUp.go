package signUp

import (
	"context"
	"net/http"
	"time"
	"vkid-backend/internal/cache"
	"vkid-backend/internal/storage"
	"vkid-backend/internal/storage/models"

	"github.com/gin-gonic/gin"
	"github.com/gofrs/uuid"
	"golang.org/x/crypto/bcrypt"
)

func SignUp(c *gin.Context) {
	// Get name, email, password off req body
	var body struct {
		Username string    `json:"username"`
		Email    string    `json:"email"`
		Password string    `json:"password"`
		RoleId   uuid.UUID `json:"role_id"`
	}

	if err := c.ShouldBindJSON(&body); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error":   "Failed to get body",
			"details": err.Error(),
		})
		return
	}

	hash, err := bcrypt.GenerateFromPassword([]byte(body.Password), 10)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Failed to generate hashed password",
		})

		return
	}

	userId, err := uuid.NewV6()
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error":       err.Error(),
			"description": "Failed to generate user id",
		})

		return
	}

	user := models.User{
		Id:           userId,
		Username:     body.Username,
		Email:        body.Email,
		PasswordHash: string(hash),
		RoleId:       body.RoleId,
	}

	result := storage.DB.Create(&user)
	if result.Error != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to create user",
		})
		return
	}

	// Кэшируем нового пользователя
	if cache.IsGlobalCacheReady() {
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()

		forumCache := cache.GetGlobalForumCache()
		if err := forumCache.CacheUser(ctx, user.Id.String(), user); err != nil {
			// Логируем ошибку, но не прерываем выполнение
			c.Header("Cache-Warning", "Failed to cache new user")
		}
	}

	c.JSON(http.StatusOK, gin.H{
		"message": "User created successfully",
		"user":    user,
	})
}
