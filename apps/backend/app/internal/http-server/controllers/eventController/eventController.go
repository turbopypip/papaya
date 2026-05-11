package eventController

import (
	"io"
	"net/http"
	"papaya-backend/internal/realtime"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/gofrs/uuid"
)

type Impl struct{}

func (r Impl) SubscribeThread(c *gin.Context) {
	threadID, err := uuid.FromString(c.Param("threadId"))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid thread id"})
		return
	}

	events, unsubscribe := realtime.DefaultHub.Subscribe(threadID.String())
	defer unsubscribe()

	c.Header("Content-Type", "text/event-stream")
	c.Header("Cache-Control", "no-cache")
	c.Header("Connection", "keep-alive")
	c.Header("X-Accel-Buffering", "no")

	heartbeat := time.NewTicker(25 * time.Second)
	defer heartbeat.Stop()

	c.Stream(func(w io.Writer) bool {
		select {
		case event, ok := <-events:
			if !ok {
				return false
			}
			c.SSEvent(event.Type, event)
			return true
		case <-heartbeat.C:
			c.SSEvent("ping", gin.H{"type": "ping", "thread_id": threadID.String()})
			return true
		case <-c.Request.Context().Done():
			return false
		}
	})
}
