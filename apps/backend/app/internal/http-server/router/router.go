package router

import (
	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
	"os"
	"papaya-backend/internal/http-server/middleware"
	"papaya-backend/internal/http-server/router/registerRoutes"
)

func InitRouter() *gin.Engine {
	// Base url for api version 1
	const baseUrlV1 = "/api/v1"

	// Init router
	router := gin.Default()

	// Make visible files in uploads dir
	router.Static("/uploads", os.Getenv("UPLOADS_PATH"))

	// Apply CORS middleware
	router.Use(cors.New(cors.Config{
		AllowOrigins:     []string{"http://localhost:3000"}, // Allow test requests from frontend
		AllowMethods:     []string{"GET", "POST", "PUT", "DELETE"},
		AllowHeaders:     []string{"Content-Type", "Authorization"},
		AllowCredentials: true, // Allow credentials (e.g., cookies)
	}))

	// Http requests route groups
	// main
	api := router.Group(baseUrlV1)

	// Test
	registerRoutes.Test(api)

	// Auth
	authRoutes := api.Group("/auth")
	registerRoutes.Auth(authRoutes)

	// Thread
	threadRoutes := api.Group("/thread")
	threadRoutes.Use(middleware.Auth)
	registerRoutes.Thread(threadRoutes)

	// Role
	roleRoutes := api.Group("/role")
	registerRoutes.Role(roleRoutes)

	// Post
	postRoutes := api.Group("/post")
	postRoutes.Use(middleware.Auth)
	registerRoutes.Post(postRoutes)

	// Comment
	commentRoutes := api.Group("/comment")
	commentRoutes.Use(middleware.Auth)
	registerRoutes.Comment(commentRoutes)

	// Like
	likeRoutes := api.Group("/like")
	likeRoutes.Use(middleware.Auth)
	registerRoutes.Like(likeRoutes)

	// User
	userRoutes := api.Group("/user")
	userRoutes.Use(middleware.Auth)
	registerRoutes.User(userRoutes)

	registerRoutes.AttachmentRoutes(router, baseUrlV1)

	return router
}
