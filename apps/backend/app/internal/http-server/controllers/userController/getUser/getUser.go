package getUser

import (
	"github.com/gin-gonic/gin"
	"net/http"
	"papaya-backend/internal/storage"
	"papaya-backend/internal/storage/models"
)

func GetUser(c *gin.Context) {
	user, _ := c.Get("user")
	userData := user.(models.User)

	var role models.Role
	if err := storage.DB.First(&role, "id = ?", userData.RoleId).Error; err != nil {
		c.JSON(http.StatusOK, gin.H{
			"user": gin.H{
				"ID":        userData.Id,
				"username":  userData.Username,
				"email":     userData.Email,
				"role_id":   userData.RoleId,
				"CreatedAt": userData.CreatedAt,
				"UpdatedAt": userData.UpdatedAt,
			},
		})
		return
	}

	// Send data
	c.JSON(http.StatusOK, gin.H{
		"user": gin.H{
			"ID":        userData.Id,
			"username":  userData.Username,
			"email":     userData.Email,
			"role_id":   userData.RoleId,
			"CreatedAt": userData.CreatedAt,
			"UpdatedAt": userData.UpdatedAt,
			"role": gin.H{
				"ID":          role.Id,
				"name":        role.Name,
				"permissions": role.Permissions,
			},
		},
	})
}
