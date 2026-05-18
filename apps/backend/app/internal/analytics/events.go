package analytics

import "github.com/gofrs/uuid"

const (
	EventThreadViewed   = "thread_viewed"
	EventThreadCreated  = "thread_created"
	EventPostCreated    = "post_created"
	EventCommentCreated = "comment_created"
	EventPostLiked      = "post_liked"
	EventCommentLiked   = "comment_liked"

	EntityThread  = "thread"
	EntityPost    = "post"
	EntityComment = "comment"
)

type Event struct {
	UserID     uuid.UUID
	EventType  string
	EntityType string
	EntityID   uuid.UUID
	ThreadID   uuid.UUID
	Metadata   map[string]any
}
