package likeController

import (
	"github.com/gin-gonic/gin"
	"vkid-backend/internal/http-server/controllers/likeController/createLike"
	"vkid-backend/internal/http-server/controllers/likeController/deleteLike" // ⬅️ добавлено
	"vkid-backend/internal/http-server/controllers/likeController/getLikes"
)

type LikeController interface {
	CreateLike(c *gin.Context)
	GetLikes(c *gin.Context)
	DeleteLike(c *gin.Context) // ⬅️ добавлено
}

type Impl struct{}

func (r Impl) CreateLike(c *gin.Context) {
	createLike.CreateLike(c)
}

func (r Impl) GetLikes(c *gin.Context) {
	getLikes.GetLikes(c)
}

func (r Impl) DeleteLike(c *gin.Context) { // ⬅️ добавлено
	deleteLike.DeleteLike(c)
}
