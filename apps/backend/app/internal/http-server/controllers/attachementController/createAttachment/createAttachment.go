package createAttachment

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/gofrs/uuid"
	"gorm.io/gorm"

	"papaya-backend/internal/attachments"
	"papaya-backend/internal/storage"
	"papaya-backend/internal/storage/models"
)

func CreateAttachment(c *gin.Context) {
	ownerType := c.PostForm("owner_type")
	if ownerType == "" {
		ownerType = c.GetHeader("owner_type")
	}

	ownerIDValue := c.PostForm("owner_id")
	if ownerIDValue == "" {
		ownerIDValue = c.GetHeader("owner_id")
	}

	if ownerType != attachments.OwnerTypeThread &&
		ownerType != attachments.OwnerTypePost &&
		ownerType != attachments.OwnerTypeComment {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid owner_type"})
		return
	}

	ownerID, err := uuid.FromString(ownerIDValue)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid owner_id"})
		return
	}

	user, _ := c.Get("user")
	userData := user.(models.User)

	var savedFiles []string
	var createdAttachments []models.Attachment
	err = storage.DB.Transaction(func(tx *gorm.DB) error {
		var err error
		createdAttachments, savedFiles, err = attachments.CreateFromRequest(c, tx, ownerType, ownerID, userData.Id)
		return err
	})
	if err != nil {
		attachments.CleanupFiles(savedFiles)
		if attachments.IsValidationError(err) {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to create attachment"})
		return
	}
	if len(createdAttachments) == 0 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "File is required"})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"message":     "created attachment",
		"attachments": createdAttachments,
	})
}
