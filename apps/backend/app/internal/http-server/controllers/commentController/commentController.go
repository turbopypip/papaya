package commentController

import (
	"github.com/gin-gonic/gin"
	"papaya-backend/internal/http-server/controllers/commentController/createComment"
	getCommentsWithPostId "papaya-backend/internal/http-server/controllers/commentController/getCommentsByPostId"
)

// CommentController defines methods for managing roles.
type CommentController interface {
	// CreateComment saves a new Comment
	CreateComment(c *gin.Context)

	GetCommentsWithPostId(c *gin.Context)
}

type Impl struct{}

// CreateComment saves a new Comment
func (r Impl) CreateComment(c *gin.Context) {
	createComment.CreateComment(c)
}

func (r Impl) GetCommentsWithPostId(c *gin.Context) {
	getCommentsWithPostId.GetCommentsByPostId(c)
}
