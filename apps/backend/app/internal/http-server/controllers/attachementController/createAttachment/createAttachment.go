package createAttachment

import (
	"github.com/gin-gonic/gin"
	"github.com/gofrs/uuid"
	"net/http"
	"os"
	"papaya-backend/internal/storage"
	"papaya-backend/internal/storage/models"
	"path/filepath"
)

func CreateAttachment(c *gin.Context) {
	// Accept metadata in query headers
	threadIdHeader := c.GetHeader("thread_id")
	postIdHeader := c.GetHeader("post_id")

	// Check if ids exist in headers and parse them
	threadId, err := uuid.FromString(threadIdHeader)
	if err != nil {
		c.JSON(http.StatusBadRequest,
			gin.H{
				"error": "Invalid ThreadId",
			})
		return
	}
	postId, err := uuid.FromString(postIdHeader)
	if err != nil {
		c.JSON(http.StatusBadRequest,
			gin.H{
				"error": "Invalid PostId",
			})
		return
	}

	// Getting the file from request
	file, err := c.FormFile("file")
	if err != nil {
		c.JSON(http.StatusBadRequest,
			gin.H{
				"error": "File is required",
			})
		return
	}

	// Create an attachment id
	attachmentId, err := uuid.NewV6()
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Failed to create an attachment id",
		})
		return
	}

	// Using attachment id as its filename
	filename := attachmentId.String() + filepath.Ext(file.Filename)
	filePath := os.Getenv("UPLOADS_PATH") + filename

	// Saving attachment in uploads folder
	if err := c.SaveUploadedFile(file, filePath); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to save file",
		})
		return
	}

	// Generating url to file
	fileUrl := filename

	// Init attachment
	attachment := models.Attachment{
		Id:       attachmentId,
		Url:      fileUrl,
		ThreadId: threadId,
		PostId:   postId,
	}

	// Save attachment
	result := storage.DB.Create(&attachment)
	if result.Error != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to create attachment",
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"message":    "User created successfully",
		"attachment": attachment,
	})
}
