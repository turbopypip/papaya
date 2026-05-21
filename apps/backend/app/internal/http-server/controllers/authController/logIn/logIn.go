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
			"error": "Не удалось прочитать данные для входа",
		})
		return
	}

	var user models.User
	storage.DB.First(&user, "email = ?", body.Email)
	if user.Username == "" {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Неверный email или пароль",
		})

		return
	}

	err := bcrypt.CompareHashAndPassword([]byte(user.PasswordHash), []byte(body.Password))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Неверный email или пароль",
		})

		return
	}

	if err := serverAuth.SetAuthCookie(c, user); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Не удалось создать токен авторизации",
		})

		return
	}

	c.JSON(http.StatusOK, gin.H{})
}
