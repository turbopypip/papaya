package deleteComment

import (
	"context"
	"errors"
	"net/http"
	"papaya-backend/internal/attachments"
	"papaya-backend/internal/cache"
	"papaya-backend/internal/realtime"
	"papaya-backend/internal/storage"
	"papaya-backend/internal/storage/models"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/gofrs/uuid"
	"gorm.io/gorm"
)

func DeleteComment(c *gin.Context) {
	commentID, err := uuid.FromString(c.Param("id"))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid comment id"})
		return
	}

	user, _ := c.Get("user")
	userData := user.(models.User)

	var comment models.Comment
	if err := storage.DB.First(&comment, "id = ?", commentID).Error; errors.Is(err, gorm.ErrRecordNotFound) {
		c.JSON(http.StatusNotFound, gin.H{"error": "Comment not found"})
		return
	} else if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to retrieve comment"})
		return
	}

	if !canDeleteComment(userData, comment) {
		c.JSON(http.StatusForbidden, gin.H{"error": "You cannot delete this comment"})
		return
	}

	var post models.Post
	if err := storage.DB.First(&post, "id = ?", comment.PostId).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to retrieve comment post"})
		return
	}

	var removedFiles []string
	err = storage.DB.Transaction(func(tx *gorm.DB) error {
		if err := tx.
			Where("likable_type = ? AND likable_id = ?", models.LikableComment, comment.Id).
			Delete(&models.Like{}).Error; err != nil {
			return err
		}

		commentAttachmentPaths, err := attachments.DeleteForOwners(
			tx,
			attachments.OwnerTypeComment,
			[]uuid.UUID{comment.Id},
		)
		if err != nil {
			return err
		}
		removedFiles = append(removedFiles, commentAttachmentPaths...)

		return tx.Delete(&comment).Error
	})
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to delete comment"})
		return
	}
	attachments.CleanupFiles(removedFiles)

	invalidateCache(c, post)
	realtime.DefaultHub.Publish(post.ThreadId.String(), realtime.Event{
		Type:      realtime.EventCommentDeleted,
		ThreadID:  post.ThreadId.String(),
		PostID:    comment.PostId.String(),
		CommentID: comment.Id.String(),
	})

	c.JSON(http.StatusOK, gin.H{
		"message":    "deleted comment",
		"comment_id": comment.Id,
	})
}

func canDeleteComment(user models.User, comment models.Comment) bool {
	var role models.Role
	if err := storage.DB.First(&role, "id = ?", user.RoleId).Error; err != nil {
		return comment.UserId == user.Id
	}

	if comment.UserId == user.Id && role.Permissions.Comments.DeleteOwn {
		return true
	}

	return role.Permissions.Comments.DeleteAny
}

func invalidateCache(c *gin.Context, post models.Post) {
	if !cache.IsGlobalCacheReady() {
		return
	}

	ctx, cancel := context.WithTimeout(c.Request.Context(), 5*time.Second)
	defer cancel()

	forumCache := cache.GetGlobalForumCache()
	if err := forumCache.InvalidatePost(ctx, post.Id.String()); err != nil {
		c.Header("Cache-Warning", "Failed to invalidate post cache")
	}
	if err := forumCache.InvalidateThread(ctx, post.ThreadId.String()); err != nil {
		c.Header("Cache-Warning", "Failed to invalidate thread cache")
	}
}
