package models

import (
	"github.com/gofrs/uuid"
	"gorm.io/gorm"
)

type Post struct {
	gorm.Model
	Id          uuid.UUID    `json:"ID" gorm:"primary_key"`
	Content     string       `json:"content"`
	UserId      uuid.UUID    `json:"user_id" gorm:"references:User"`
	ThreadId    uuid.UUID    `json:"thread_id" gorm:"references:Thread"`
	Likes       []Like       `json:"likes" gorm:"polymorphic:Likable;"`
	Attachments []Attachment `json:"attachments" gorm:"-"`
}
