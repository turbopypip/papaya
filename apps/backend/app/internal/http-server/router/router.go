package router

import (
	"os"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
	"papaya-backend/internal/attachments"
	"papaya-backend/internal/http-server/middleware"
	"papaya-backend/internal/http-server/router/registerRoutes"
)

func InitRouter() *gin.Engine {
	// Base url for api version 1
	const baseUrlV1 = "/api/v1"

	// Init router
	router := gin.Default()

	// Make visible files in uploads dir
	if err := os.MkdirAll(attachments.UploadDir(), 0755); err == nil {
		router.Static("/uploads", attachments.UploadDir())
	}

	// Apply CORS middleware
	router.Use(cors.New(cors.Config{
		AllowOrigins:     []string{"http://localhost:3000"}, // Allow test requests from frontend
		AllowMethods:     []string{"GET", "POST", "PUT", "DELETE", "OPTIONS"},
		AllowHeaders:     []string{"Content-Type", "Authorization", "owner_type", "owner_id"},
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

	// Realtime events
	eventRoutes := api.Group("/events")
	eventRoutes.Use(middleware.Auth)
	registerRoutes.Events(eventRoutes)

	// Role
	roleRoutes := api.Group("/role")
	roleRoutes.Use(middleware.Auth)
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
