package models

import (
	"github.com/gofrs/uuid"
	"gorm.io/gorm"
)

const (
	LikablePost    = "post"
	LikableComment = "comment"
)

type Like struct {
	gorm.Model
	Id          uuid.UUID `json:"ID" gorm:"primary_key"`
	UserId      uuid.UUID `json:"user_id" gorm:"references:User"`
	LikableID   uuid.UUID `json:"likable_id"`
	LikableType string    `json:"likable_type"` // "post" or "comment"
}
