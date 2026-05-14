package createAttachment

import (
	"errors"
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/gofrs/uuid"
	"gorm.io/gorm"

	"papaya-backend/internal/attachments"
	"papaya-backend/internal/http-server/rbac"
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
	if !canAttachToOwner(c, ownerType, ownerID) {
		return
	}

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

func canAttachToOwner(c *gin.Context, ownerType string, ownerID uuid.UUID) bool {
	switch ownerType {
	case attachments.OwnerTypeThread:
		var thread models.Thread
		if err := storage.DB.First(&thread, "id = ?", ownerID).Error; err != nil {
			abortMissingOwner(c, err)
			return false
		}
		if rbac.Can(c, rbac.ResourceThreads, rbac.ActionUpdate, thread.UserId) {
			return true
		}
	case attachments.OwnerTypePost:
		var post models.Post
		if err := storage.DB.First(&post, "id = ?", ownerID).Error; err != nil {
			abortMissingOwner(c, err)
			return false
		}
		if rbac.Can(c, rbac.ResourcePosts, rbac.ActionUpdate, post.UserId) {
			return true
		}
	case attachments.OwnerTypeComment:
		var comment models.Comment
		if err := storage.DB.First(&comment, "id = ?", ownerID).Error; err != nil {
			abortMissingOwner(c, err)
			return false
		}
		if rbac.Can(c, rbac.ResourceComments, rbac.ActionUpdate, comment.UserId) {
			return true
		}
	}

	rbac.AbortForbidden(c, "You cannot attach files to this content")
	return false
}

func abortMissingOwner(c *gin.Context, err error) {
	if errors.Is(err, gorm.ErrRecordNotFound) {
		c.JSON(http.StatusNotFound, gin.H{"error": "Attachment owner not found"})
		return
	}

	c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to retrieve attachment owner"})
}
