package models

import (
	"github.com/gofrs/uuid"
	"github.com/lib/pq"
	"gorm.io/gorm"
)

type Thread struct {
	gorm.Model
	Id          uuid.UUID      `json:"ID" gorm:"primary_key"`
	Title       string         `json:"title" gorm:"index;unique"`
	Categories  pq.StringArray `json:"categories" gorm:"type:text[]"`
	UserId      uuid.UUID      `json:"user_id" gorm:"references:User"`
	Attachments []Attachment   `json:"attachments" gorm:"-"`
}
