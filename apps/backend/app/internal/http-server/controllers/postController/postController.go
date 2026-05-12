package postController

import (
	"github.com/gin-gonic/gin"
	"papaya-backend/internal/http-server/controllers/postController/createPost"
	"papaya-backend/internal/http-server/controllers/postController/deletePost"
	"papaya-backend/internal/http-server/controllers/postController/getPostsWithThreadId"
	"papaya-backend/internal/http-server/controllers/postController/updatePost"
)

// PostController defines methods for managing posts.
type PostController interface {
	// CreatePost saves a new Post
	CreatePost(c *gin.Context)

	GetPostsWithThreadId(c *gin.Context)

	UpdatePost(c *gin.Context)

	DeletePost(c *gin.Context)
}

type Impl struct{}

// CreatePost saves a new Post
func (r Impl) CreatePost(c *gin.Context) {
	createPost.CreatePost(c)
}

func (r Impl) GetPostsWithThreadId(c *gin.Context) {
	getPostsWithThreadId.GetPostsWithThreadId(c)
}

func (r Impl) UpdatePost(c *gin.Context) {
	updatePost.UpdatePost(c)
}

func (r Impl) DeletePost(c *gin.Context) {
	deletePost.DeletePost(c)
}
