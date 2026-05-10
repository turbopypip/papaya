// TODO: test error handling

package getLikes

import (
	"github.com/gin-gonic/gin"
	"github.com/gofrs/uuid"
	"github.com/sirupsen/logrus"
	"net/http"
	"papaya-backend/internal/storage"
	"papaya-backend/internal/storage/models"
	"sync"
)

type LikeResult struct {
	LikableID     string `json:"likable_id"`
	LikableType   string `json:"likable_type"`
	LikeCount     int    `json:"like_count"`
	IsLikedByUser bool   `json:"is_liked_by_user"`
	ErrorMessage  string `json:"error,omitempty"`
}

func LoadLikesCount(likableID uuid.UUID, likableType string, userID uuid.UUID) (int, bool, error) {

	var result struct {
		LikeCount     int
		IsLikedByUser bool
	}

	// Query the database for likes
	err := storage.DB.Raw(`
		SELECT
			COUNT(*) AS like_count,
			COUNT(CASE WHEN user_id = ? THEN 1 END) > 0 AS is_liked_by_user
		FROM likes
		WHERE likable_id = ? AND likable_type = ?
	`, userID, likableID, likableType).Scan(&result).Error
	if err != nil {
		return 0, false, err
	}

	// Return the count of likes
	return result.LikeCount, result.IsLikedByUser, nil
}

func GetLikes(c *gin.Context) {
	var body struct {
		Likables []struct {
			ID   string `json:"likable_id"`
			Type string `json:"likable_type"`
		} `json:"likables"`
	}

	// Check if body exists
	if err := c.BindJSON(&body); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request format"})
		return
	}

	// load user from context, it should exist after authentication
	user, _ := c.Get("user")
	userData := user.(models.User)

	// An array with like counts
	results := make([]LikeResult, len(body.Likables))
	var wg sync.WaitGroup
	var stopSignal = make(chan struct{})
	errorChan := make(chan error, 1)

	for i, likable := range body.Likables {
		// check if
		if likable.Type == "" || likable.ID == "" {
			c.JSON(http.StatusBadRequest, gin.H{"error": "expected 2 args. 1 or 0 given", "likeable": likable})
			return
		}

		id, err := uuid.FromString(likable.ID)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}

		wg.Add(1)
		go func(i int, id uuid.UUID, t string) {
			defer wg.Done()
			select {
			case <-stopSignal:
				return
			default:
				count, isLikedByUser, err := LoadLikesCount(id, t, userData.Id)

				if err != nil {
					// sending first error
					select {
					case errorChan <- err: // Sending error
					default: // If already send an error do nothing
					}
					close(stopSignal) // closing goroutines
					return
				}

				results[i] = LikeResult{
					LikableID:     id.String(),
					LikableType:   t,
					IsLikedByUser: isLikedByUser,
					LikeCount:     count,
				}
			}
		}(i, id, likable.Type)
	}
	wg.Wait()

	// error check
	select {
	case err := <-errorChan: // If got an error
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	default: // No errors
	}

	logrus.Info(results)
	// Sending results to user
	c.JSON(http.StatusOK, gin.H{"results": results})
}
