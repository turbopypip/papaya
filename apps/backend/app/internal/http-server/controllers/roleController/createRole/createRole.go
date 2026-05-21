package createRole

import (
	"github.com/gin-gonic/gin"
	"github.com/gofrs/uuid"
	"net/http"
	"papaya-backend/internal/storage"
	"papaya-backend/internal/storage/models"
)

// CreateRole добавляет новую роль в базу данных
func CreateRole(c *gin.Context) {

	var body struct {
		Title       string             `json:"title"`
		Permissions models.Permissions `json:"permissions"`
	}

	if err := c.BindJSON(&body); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Не удалось прочитать данные роли",
		})
		return
	}

	roleId, err := uuid.NewV6()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Не удалось создать идентификатор роли",
		})
		return
	}

	role := models.Role{
		Id:          roleId,
		Name:        body.Title,
		Permissions: body.Permissions,
	}

	result := storage.DB.Create(&role)
	if result.Error != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Не удалось сохранить роль",
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"message": "Роль успешно создана",
		"role":    role,
	})
}
