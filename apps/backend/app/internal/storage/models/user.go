package models

import (
	"github.com/gofrs/uuid"
	"gorm.io/gorm"
)

type ResourcePermissions struct {
	Create    bool `json:"create"`
	Read      bool `json:"read"`
	UpdateOwn bool `json:"update_own"`
	UpdateAny bool `json:"update_any"`
	DeleteOwn bool `json:"delete_own"`
	DeleteAny bool `json:"delete_any"`
}

type UserPermissions struct {
	Create    bool `json:"create"`
	Read      bool `json:"read"`
	UpdateOwn bool `json:"update_own"`
	UpdateAny bool `json:"update_any"`
	DeleteOwn bool `json:"delete_own"`
	DeleteAny bool `json:"delete_any"`
	Ban       bool `json:"ban"`
}

type Permissions struct {
	Threads     ResourcePermissions `json:"threads"`
	Posts       ResourcePermissions `json:"posts"`
	Comments    ResourcePermissions `json:"comments"`
	Categories  ResourcePermissions `json:"categories"`
	Likes       ResourcePermissions `json:"likes"`
	Attachments ResourcePermissions `json:"attachments"`
	Users       UserPermissions     `json:"users"`
}

type Role struct {
	gorm.Model
	Id          uuid.UUID   `json:"ID" gorm:"primary_key"`
	Name        string      `json:"name" gorm:"index;unique"`
	Permissions Permissions `json:"permissions" gorm:"type:jsonb;serializer:json"`
}

type User struct {
	gorm.Model
	Id           uuid.UUID `json:"ID" gorm:"primary_key"`
	Username     string    `json:"username" gorm:"index;unique"`
	Email        string    `json:"email" gorm:"index;unique"`
	PasswordHash string    `json:"password_hash" gorm:"index"`
	RoleId       uuid.UUID `json:"role_id" gorm:"references:Role"`
}
