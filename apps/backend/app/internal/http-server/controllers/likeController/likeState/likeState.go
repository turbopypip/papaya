package likeState

import (
	"errors"
	"net/http"
	"papaya-backend/internal/storage"
	"papaya-backend/internal/storage/models"

	"github.com/gin-gonic/gin"
	"github.com/gofrs/uuid"
)

type Result struct {
	LikableID   string `json:"likable_id"`
	LikableType string `json:"likable_type"`
	Count       int64  `json:"count"`
	LikedByMe   bool   `json:"liked_by_me"`
}

func ValidateLikableType(likableType string) bool {
	return likableType == models.LikablePost || likableType == models.LikableComment
}

func CurrentUser(c *gin.Context) (models.User, bool) {
	user, ok := c.Get("user")
	if !ok {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "Unauthorized"})
		return models.User{}, false
	}

	userData, ok := user.(models.User)
	if !ok {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "Unauthorized"})
		return models.User{}, false
	}

	return userData, true
}

func Load(likableID uuid.UUID, likableType string, userID uuid.UUID) (Result, error) {
	var count int64
	if err := storage.DB.Model(&models.Like{}).
		Where("likable_id = ? AND likable_type = ?", likableID, likableType).
		Count(&count).Error; err != nil {
		return Result{}, err
	}

	var likedCount int64
	if err := storage.DB.Model(&models.Like{}).
		Where("user_id = ? AND likable_id = ? AND likable_type = ?", userID, likableID, likableType).
		Count(&likedCount).Error; err != nil {
		return Result{}, err
	}

	return Result{
		LikableID:   likableID.String(),
		LikableType: likableType,
		Count:       count,
		LikedByMe:   likedCount > 0,
	}, nil
}

func ResolveThreadID(likableID uuid.UUID, likableType string) (uuid.UUID, bool, error) {
	switch likableType {
	case models.LikablePost:
		var post models.Post
		if err := storage.DB.First(&post, "id = ?", likableID).Error; err != nil {
			return uuid.Nil, false, err
		}
		return post.ThreadId, true, nil
	case models.LikableComment:
		var comment models.Comment
		if err := storage.DB.First(&comment, "id = ?", likableID).Error; err != nil {
			return uuid.Nil, false, err
		}

		var post models.Post
		if err := storage.DB.First(&post, "id = ?", comment.PostId).Error; err != nil {
			return uuid.Nil, false, err
		}
		return post.ThreadId, true, nil
	default:
		return uuid.Nil, false, errors.New("invalid likable type")
	}
}
