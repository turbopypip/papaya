package auth

import (
	"net/http"
	"os"
	"papaya-backend/internal/config"
	"strconv"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/golang-jwt/jwt/v5"
	"papaya-backend/internal/storage/models"
)

func SetAuthCookie(c *gin.Context, user models.User) error {
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, jwt.MapClaims{
		"sub": user.Id,
		"exp": time.Now().Add(time.Hour * 24 * 30).Unix(),
	})

	tokenString, err := token.SignedString([]byte(os.Getenv("SECRET")))
	if err != nil {
		return err
	}

	c.SetSameSite(cookieSameSite())
	c.SetCookie(
		"Authorization",
		tokenString,
		3600*24*30,
		"/",
		os.Getenv("AUTH_COOKIE_DOMAIN"),
		cookieSecure(),
		true,
	)

	return nil
}

func ClearAuthCookie(c *gin.Context) {
	c.SetSameSite(cookieSameSite())
	c.SetCookie("Authorization", "", -1, "/", os.Getenv("AUTH_COOKIE_DOMAIN"), cookieSecure(), true)
	c.SetCookie("Authorization", "", -1, "", "", false, true)
}

func cookieSameSite() http.SameSite {
	switch strings.ToLower(strings.TrimSpace(os.Getenv("AUTH_COOKIE_SAME_SITE"))) {
	case "strict":
		return http.SameSiteStrictMode
	case "none":
		return http.SameSiteNoneMode
	default:
		return http.SameSiteLaxMode
	}
}

func cookieSecure() bool {
	value := strings.TrimSpace(os.Getenv("AUTH_COOKIE_SECURE"))
	if value != "" {
		secure, err := strconv.ParseBool(value)
		return err == nil && secure
	}

	return config.CurrentEnv() == "prod"
}
