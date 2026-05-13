package commentController

import (
	"github.com/gin-gonic/gin"
	"papaya-backend/internal/http-server/controllers/commentController/createComment"
	"papaya-backend/internal/http-server/controllers/commentController/deleteComment"
	getCommentsWithPostId "papaya-backend/internal/http-server/controllers/commentController/getCommentsByPostId"
	"papaya-backend/internal/http-server/controllers/commentController/updateComment"
)

// CommentController defines methods for managing roles.
type CommentController interface {
	// CreateComment saves a new Comment
	CreateComment(c *gin.Context)

	GetCommentsWithPostId(c *gin.Context)

	UpdateComment(c *gin.Context)

	DeleteComment(c *gin.Context)
}

type Impl struct{}

// CreateComment saves a new Comment
func (r Impl) CreateComment(c *gin.Context) {
	createComment.CreateComment(c)
}

func (r Impl) GetCommentsWithPostId(c *gin.Context) {
	getCommentsWithPostId.GetCommentsByPostId(c)
}

func (r Impl) UpdateComment(c *gin.Context) {
	updateComment.UpdateComment(c)
}

func (r Impl) DeleteComment(c *gin.Context) {
	deleteComment.DeleteComment(c)
}
