package models

import (
	"github.com/gofrs/uuid"
	"gorm.io/gorm"
)

// Permissions Refactor if needed
type Permissions struct {
	Threads struct {
		Create bool `json:"create"`
		Read   bool `json:"get"`
		Update bool `json:"update"`
		Delete bool `json:"delete"`
	} `json:"threads"`
	Comments struct {
		Create bool `json:"create"`
		Read   bool `json:"get"`
		Update bool `json:"update"`
		Delete bool `json:"delete"`
	} `json:"comments"`
	Users struct {
		Create bool `json:"create"`
		Read   bool `json:"get"`
		Update bool `json:"update"`
		Delete bool `json:"delete"`
	} `json:"userController"`
	Categories struct {
		Create bool `json:"create"`
		Read   bool `json:"get"`
		Update bool `json:"update"`
		Delete bool `json:"delete"`
	} `json:"categories"`
}

type Role struct {
	gorm.Model
	Id          uuid.UUID   `json:"ID" gorm:"primary_key"`
	Name        string      `json:"name" gorm:"index;unique"`
	Permissions Permissions `json:"permissions" gorm:"type:jsonb"`
}

type User struct {
	gorm.Model
	Id           uuid.UUID `json:"ID" gorm:"primary_key"`
	Username     string    `json:"username" gorm:"index;unique"`
	Email        string    `json:"email" gorm:"index;unique"`
	PasswordHash string    `json:"password_hash" gorm:"index"`
	RoleId       uuid.UUID `json:"role_id" gorm:"references:Role"`
}
