package storage

import (
	"errors"
	"os"
	"papaya-backend/internal/config"
	"papaya-backend/internal/storage/models"
	"strings"

	"github.com/gofrs/uuid"
	"github.com/sirupsen/logrus"
	"golang.org/x/crypto/bcrypt"
	"gorm.io/gorm"
)

var (
	DefaultUserRoleID  = mustRoleID("1ef94a6d-ed65-6cd0-bfb7-718b8878121a")
	DefaultAdminRoleID = mustRoleID("1ef94a6d-ed65-6d36-bfb7-718b8878121b")
	DefaultDevUserID   = mustRoleID("1ef94a6d-ed65-6e14-bfb7-718b8878121c")
)

const (
	DevUserUsername = "dev-user"
	DevUserEmail    = "dev@papaya.local"
	DevUserPassword = "papaya-dev-password"
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

func SeedDevUser() {
	if !config.IsDev() {
		return
	}

	hash, err := bcrypt.GenerateFromPassword([]byte(DevUserPassword), 10)
	if err != nil {
		logrus.Fatalf("Failed to generate dev user password hash: %v", err)
	}

	seededUser := models.User{
		Id:           DefaultDevUserID,
		Username:     DevUserUsername,
		Email:        DevUserEmail,
		PasswordHash: string(hash),
		RoleId:       devUserRoleID(),
	}

	var user models.User
	err = DB.Where("email = ?", DevUserEmail).First(&user).Error
	if errors.Is(err, gorm.ErrRecordNotFound) {
		if err := DB.Create(&seededUser).Error; err != nil {
			logrus.Fatalf("Failed to seed dev user: %v", err)
		}
		logrus.Info("Dev user seeded successfully")
		return
	}
	if err != nil {
		logrus.Fatalf("Failed to query dev user: %v", err)
	}

	user.Username = DevUserUsername
	user.PasswordHash = string(hash)
	user.RoleId = seededUser.RoleId
	if err := DB.Save(&user).Error; err != nil {
		logrus.Fatalf("Failed to update dev user: %v", err)
	}

	logrus.Info("Dev user seeded successfully")
}

func devUserRoleID() uuid.UUID {
	role := strings.ToLower(strings.TrimSpace(os.Getenv("DEV_USER_ROLE")))
	if role == "user" {
		return DefaultUserRoleID
	}
	if role != "" && role != "admin" {
		logrus.Warnf("Unknown DEV_USER_ROLE=%q, using admin", role)
	}

	return DefaultAdminRoleID
}

func userPermissions() models.Permissions {
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
		Threads:     ownContent,
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
