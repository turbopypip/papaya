package deleteThread

import (
	"context"
	"errors"
	"net/http"
	"papaya-backend/internal/attachments"
	"papaya-backend/internal/cache"
	"papaya-backend/internal/http-server/rbac"
	"papaya-backend/internal/realtime"
	"papaya-backend/internal/storage"
	"papaya-backend/internal/storage/models"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/gofrs/uuid"
	"gorm.io/gorm"
)

func DeleteThread(c *gin.Context) {
	threadID, err := uuid.FromString(c.Param("id"))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid thread id"})
		return
	}

	var thread models.Thread
	if err := storage.DB.First(&thread, "id = ?", threadID).Error; errors.Is(err, gorm.ErrRecordNotFound) {
		c.JSON(http.StatusNotFound, gin.H{"error": "Thread not found"})
		return
	} else if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to retrieve thread"})
		return
	}

	if !rbac.Can(c, rbac.ResourceThreads, rbac.ActionDelete, thread.UserId) {
		c.JSON(http.StatusForbidden, gin.H{"error": "You cannot delete this thread"})
		return
	}

	var removedFiles []string
	var postIDs []uuid.UUID
	err = storage.DB.Transaction(func(tx *gorm.DB) error {
		var posts []models.Post
		if err := tx.Where("thread_id = ?", thread.Id).Find(&posts).Error; err != nil {
			return err
		}

		postIDs = make([]uuid.UUID, 0, len(posts))
		for _, post := range posts {
			postIDs = append(postIDs, post.Id)
		}

		var comments []models.Comment
		if len(postIDs) > 0 {
			if err := tx.Where("post_id IN ?", postIDs).Find(&comments).Error; err != nil {
				return err
			}
		}

		commentIDs := make([]uuid.UUID, 0, len(comments))
		for _, comment := range comments {
			commentIDs = append(commentIDs, comment.Id)
		}

		if len(postIDs) > 0 {
			if err := tx.
				Where("likable_type = ? AND likable_id IN ?", models.LikablePost, postIDs).
				Delete(&models.Like{}).Error; err != nil {
				return err
			}
		}
		if len(commentIDs) > 0 {
			if err := tx.
				Where("likable_type = ? AND likable_id IN ?", models.LikableComment, commentIDs).
				Delete(&models.Like{}).Error; err != nil {
				return err
			}
		}

		threadAttachmentPaths, err := attachments.DeleteForOwners(
			tx,
			attachments.OwnerTypeThread,
			[]uuid.UUID{thread.Id},
		)
		if err != nil {
			return err
		}
		removedFiles = append(removedFiles, threadAttachmentPaths...)

		postAttachmentPaths, err := attachments.DeleteForOwners(
			tx,
			attachments.OwnerTypePost,
			postIDs,
		)
		if err != nil {
			return err
		}
		removedFiles = append(removedFiles, postAttachmentPaths...)

		commentAttachmentPaths, err := attachments.DeleteForOwners(
			tx,
			attachments.OwnerTypeComment,
			commentIDs,
		)
		if err != nil {
			return err
		}
		removedFiles = append(removedFiles, commentAttachmentPaths...)

		if len(commentIDs) > 0 {
			if err := tx.Where("id IN ?", commentIDs).Delete(&models.Comment{}).Error; err != nil {
				return err
			}
		}
		if len(postIDs) > 0 {
			if err := tx.Where("id IN ?", postIDs).Delete(&models.Post{}).Error; err != nil {
				return err
			}
		}

		return tx.Delete(&thread).Error
	})
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to delete thread"})
		return
	}
	attachments.CleanupFiles(removedFiles)

	invalidateCache(c, thread, postIDs)
	realtime.DefaultHub.Publish(thread.Id.String(), realtime.Event{
		Type:     realtime.EventThreadDeleted,
		ThreadID: thread.Id.String(),
	})

	c.JSON(http.StatusOK, gin.H{
		"message":   "deleted thread",
		"thread_id": thread.Id,
	})
}

func invalidateCache(c *gin.Context, thread models.Thread, postIDs []uuid.UUID) {
	if !cache.IsGlobalCacheReady() {
		return
	}

	ctx, cancel := context.WithTimeout(c.Request.Context(), 5*time.Second)
	defer cancel()

	forumCache := cache.GetGlobalForumCache()
	if err := forumCache.InvalidateThread(ctx, thread.Id.String()); err != nil {
		c.Header("Cache-Warning", "Failed to invalidate thread cache")
	}
	for _, postID := range postIDs {
		if err := forumCache.InvalidatePost(ctx, postID.String()); err != nil {
			c.Header("Cache-Warning", "Failed to invalidate post cache")
			return
		}
	}
}
