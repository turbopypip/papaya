package createComment

import (
	"github.com/gin-gonic/gin"
	"github.com/gofrs/uuid"
	"net/http"
	"papaya-backend/internal/realtime"
	"papaya-backend/internal/storage"
	"papaya-backend/internal/storage/models"
)

func CreateComment(c *gin.Context) {
	var body struct {
		Content string    `json:"content"`
		PostId  uuid.UUID `json:"post_id"`
	}

	// check if body exists
	if err := c.ShouldBindJSON(&body); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error":   "Failed to get body",
			"details": err.Error(),
		})
		return
	}

	// init comment id
	commentId, err := uuid.NewV6()
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error":   err.Error(),
			"details": "Failed to generate thread id",
		})
		return
	}

	// load user from context, it should exist after authentication
	user, _ := c.Get("user")
	userData := user.(models.User)

	// init Comment
	comment := models.Comment{
		Id:      commentId,
		Content: body.Content,
		UserId:  userData.Id,
		PostId:  body.PostId,
	}

	// save Comment
	result := storage.DB.Create(&comment)
	if result.Error != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to create comment",
		})
		return
	}

	var post models.Post
	if err := storage.DB.First(&post, "id = ?", body.PostId).Error; err == nil {
		realtime.DefaultHub.Publish(post.ThreadId.String(), realtime.Event{
			Type:      realtime.EventCommentCreated,
			ThreadID:  post.ThreadId.String(),
			PostID:    body.PostId.String(),
			CommentID: commentId.String(),
		})
	}

	c.JSON(http.StatusOK, gin.H{
		"message": "created comment",
		"comment": comment,
	})
}
