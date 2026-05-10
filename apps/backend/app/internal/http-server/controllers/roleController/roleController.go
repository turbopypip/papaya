package roleController

import (
	"github.com/gin-gonic/gin"
	"vkid-backend/internal/http-server/controllers/roleController/createRole"
)

// RolesController defines methods for managing roles.
type RolesController interface {
	// CreateRole adds a new role to the database
	CreateRole(c *gin.Context)
}

type Impl struct{}

// CreateRole adds a new role to the database
func (r Impl) CreateRole(c *gin.Context) {
	createRole.CreateRole(c)
}
