package models

import (
	"github.com/gofrs/uuid"
	"gorm.io/gorm"
)

type Attachment struct {
	gorm.Model
	Id       uuid.UUID `json:"ID" gorm:"primary_key"`
	Url      string    `json:"url" gorm:"index;unique"`
	ThreadId uuid.UUID `json:"thread_id" gorm:"references:Thread"`
	PostId   uuid.UUID `json:"post_id" gorm:"references:Post"`
}
