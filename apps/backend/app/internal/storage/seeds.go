package storage

import (
	"errors"
	"papaya-backend/internal/storage/models"

	"github.com/gofrs/uuid"
	"github.com/sirupsen/logrus"
	"gorm.io/gorm"
)

var (
	DefaultUserRoleID  = mustRoleID("1ef94a6d-ed65-6cd0-bfb7-718b8878121a")
	DefaultAdminRoleID = mustRoleID("1ef94a6d-ed65-6d36-bfb7-718b8878121b")
)

func mustRoleID(value string) uuid.UUID {
	id, err := uuid.FromString(value)
	if err != nil {
		logrus.Fatalf("Failed to parse seeded role id %s: %v", value, err)
	}

	return id
}

func SeedRoles() {
	roles := []models.Role{
		{
			Id:          DefaultUserRoleID,
			Name:        "user",
			Permissions: userPermissions(),
		},
		{
			Id:          DefaultAdminRoleID,
			Name:        "admin",
			Permissions: adminPermissions(),
		},
	}

	for _, seededRole := range roles {
		var role models.Role
		err := DB.Where("name = ?", seededRole.Name).First(&role).Error
		if errors.Is(err, gorm.ErrRecordNotFound) {
			if err := DB.Create(&seededRole).Error; err != nil {
				logrus.Fatalf("Failed to seed %s role: %v", seededRole.Name, err)
			}
			continue
		}
		if err != nil {
			logrus.Fatalf("Failed to query %s role: %v", seededRole.Name, err)
		}

		role.Permissions = seededRole.Permissions
		if err := DB.Save(&role).Error; err != nil {
			logrus.Fatalf("Failed to update %s role permissions: %v", seededRole.Name, err)
		}
	}

	logrus.Info("Default roles seeded successfully")
}

func userPermissions() models.Permissions {
	readCreate := models.ResourcePermissions{
		Create: true,
		Read:   true,
	}
	ownContent := models.ResourcePermissions{
		Create:    true,
		Read:      true,
		UpdateOwn: true,
		DeleteOwn: true,
	}
	ownRelation := models.ResourcePermissions{
		Create:    true,
		Read:      true,
		DeleteOwn: true,
	}

	return models.Permissions{
		Threads:     readCreate,
		Posts:       ownContent,
		Comments:    ownContent,
		Categories:  ownContent,
		Likes:       ownRelation,
		Attachments: ownRelation,
		Users: models.UserPermissions{
			Read:      true,
			UpdateOwn: true,
		},
	}
}

func adminPermissions() models.Permissions {
	fullResource := models.ResourcePermissions{
		Create:    true,
		Read:      true,
		UpdateOwn: true,
		UpdateAny: true,
		DeleteOwn: true,
		DeleteAny: true,
	}

	return models.Permissions{
		Threads:     fullResource,
		Posts:       fullResource,
		Comments:    fullResource,
		Categories:  fullResource,
		Likes:       fullResource,
		Attachments: fullResource,
		Users: models.UserPermissions{
			Create:    true,
			Read:      true,
			UpdateOwn: true,
			UpdateAny: true,
			DeleteOwn: true,
			DeleteAny: true,
			Ban:       true,
		},
	}
}
