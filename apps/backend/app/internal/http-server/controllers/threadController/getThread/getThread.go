package getThread

import (
	"errors"
	"net/http"
	"papaya-backend/internal/attachments"
	"papaya-backend/internal/storage"
	"papaya-backend/internal/storage/models"

	"github.com/gin-gonic/gin"
	"github.com/gofrs/uuid"
	"gorm.io/gorm"
)

func GetThread(c *gin.Context) {
	threadID, err := uuid.FromString(c.Param("id"))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid thread id"})
		return
	}

	var thread models.Thread
	err = storage.DB.First(&thread, "id = ?", threadID).Error
	if errors.Is(err, gorm.ErrRecordNotFound) {
		c.JSON(http.StatusNotFound, gin.H{"error": "Thread not found"})
		return
	}
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to retrieve thread"})
		return
	}
	if err := attachments.AttachToThread(storage.DB, &thread); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to retrieve thread attachments"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"thread": thread})
}
