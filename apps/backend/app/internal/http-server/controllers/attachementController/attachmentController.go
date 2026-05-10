package attachementController

import (
	"github.com/gin-gonic/gin"
	"papaya-backend/internal/http-server/controllers/attachementController/createAttachment"
)

// AttachmentController defines methods for managing roles.
type AttachmentController interface {
	// CreateAttachment saves a new attachment
	CreateAttachment(c *gin.Context)
}

type Impl struct{}

// CreateAttachment saves a new attachment
func (r Impl) CreateAttachment(c *gin.Context) {
	createAttachment.CreateAttachment(c)
}
