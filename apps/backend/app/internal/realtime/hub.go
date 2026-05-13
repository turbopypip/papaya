package realtime

import "sync"

const (
	EventPostCreated    = "post.created"
	EventPostUpdated    = "post.updated"
	EventPostDeleted    = "post.deleted"
	EventCommentCreated = "comment.created"
	EventCommentUpdated = "comment.updated"
	EventCommentDeleted = "comment.deleted"
	EventLikeCreated    = "like.created"
	EventLikeDeleted    = "like.deleted"
	EventThreadDeleted  = "thread.deleted"
)

type Event struct {
	Type        string `json:"type"`
	ThreadID    string `json:"thread_id"`
	PostID      string `json:"post_id,omitempty"`
	CommentID   string `json:"comment_id,omitempty"`
	LikableType string `json:"likable_type,omitempty"`
	LikableID   string `json:"likable_id,omitempty"`
	Count       int64  `json:"count,omitempty"`
}

type Hub struct {
	mu      sync.RWMutex
	clients map[string]map[chan Event]struct{}
}

var DefaultHub = NewHub()

func NewHub() *Hub {
	return &Hub{
		clients: make(map[string]map[chan Event]struct{}),
	}
}

func (h *Hub) Subscribe(threadID string) (<-chan Event, func()) {
	ch := make(chan Event, 16)

	h.mu.Lock()
	if h.clients[threadID] == nil {
		h.clients[threadID] = make(map[chan Event]struct{})
	}
	h.clients[threadID][ch] = struct{}{}
	h.mu.Unlock()

	unsubscribe := func() {
		h.mu.Lock()
		defer h.mu.Unlock()

		if threadClients, ok := h.clients[threadID]; ok {
			delete(threadClients, ch)
			if len(threadClients) == 0 {
				delete(h.clients, threadID)
			}
		}
		close(ch)
	}

	return ch, unsubscribe
}

func (h *Hub) Publish(threadID string, event Event) {
	h.mu.RLock()
	defer h.mu.RUnlock()

	for ch := range h.clients[threadID] {
		select {
		case ch <- event:
		default:
		}
	}
}
