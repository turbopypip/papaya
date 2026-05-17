package models

import (
	"github.com/gofrs/uuid"
	"gorm.io/gorm"
)

type Comment struct {
	gorm.Model
	Id          uuid.UUID    `json:"ID" gorm:"primary_key"`
	Content     string       `json:"content"`
	UserId      uuid.UUID    `json:"user_id" gorm:"references:User"`
	Author      PublicUser   `json:"author" gorm:"foreignKey:UserId;references:Id"`
	PostId      uuid.UUID    `json:"post_id" gorm:"references:Post"`
	Likes       []Like       `json:"likes" gorm:"polymorphic:Likable;"`
	Attachments []Attachment `json:"attachments" gorm:"-"`
}
