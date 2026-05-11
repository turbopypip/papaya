package models

import (
	"github.com/gofrs/uuid"
	"gorm.io/gorm"
)

type Attachment struct {
	gorm.Model
	Id          uuid.UUID `json:"ID" gorm:"primary_key"`
	Url         string    `json:"url" gorm:"index;unique"`
	FileName    string    `json:"file_name"`
	ContentType string    `json:"content_type" gorm:"index"`
	Size        int64     `json:"size"`
	StorageKey  string    `json:"-" gorm:"index;unique"`
	OwnerType   string    `json:"owner_type" gorm:"index:idx_attachment_owner"`
	OwnerId     uuid.UUID `json:"owner_id" gorm:"index:idx_attachment_owner"`
	UserId      uuid.UUID `json:"user_id" gorm:"references:User"`
}
