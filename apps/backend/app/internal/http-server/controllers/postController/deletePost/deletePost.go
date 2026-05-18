package deletePost

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

func DeletePost(c *gin.Context) {
	postID, err := uuid.FromString(c.Param("id"))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Некорректный идентификатор поста"})
		return
	}

	var post models.Post
	if err := storage.DB.First(&post, "id = ?", postID).Error; errors.Is(err, gorm.ErrRecordNotFound) {
		c.JSON(http.StatusNotFound, gin.H{"error": "Пост не найден"})
		return
	} else if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Не удалось получить пост"})
		return
	}

	if !rbac.Can(c, rbac.ResourcePosts, rbac.ActionDelete, post.UserId) {
		c.JSON(http.StatusForbidden, gin.H{"error": "У вас нет прав удалить этот пост"})
		return
	}

	var removedFiles []string
	err = storage.DB.Transaction(func(tx *gorm.DB) error {
		var comments []models.Comment
		if err := tx.Where("post_id = ?", post.Id).Find(&comments).Error; err != nil {
			return err
		}

		commentIDs := make([]uuid.UUID, 0, len(comments))
		for _, comment := range comments {
			commentIDs = append(commentIDs, comment.Id)
		}

		if err := tx.
			Where("likable_type = ? AND likable_id = ?", models.LikablePost, post.Id).
			Delete(&models.Like{}).Error; err != nil {
			return err
		}

		if len(commentIDs) > 0 {
			if err := tx.
				Where("likable_type = ? AND likable_id IN ?", models.LikableComment, commentIDs).
				Delete(&models.Like{}).Error; err != nil {
				return err
			}
		}

		postAttachmentPaths, err := attachments.DeleteForOwners(
			tx,
			attachments.OwnerTypePost,
			[]uuid.UUID{post.Id},
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

		return tx.Delete(&post).Error
	})
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Не удалось удалить пост"})
		return
	}
	attachments.CleanupFiles(removedFiles)

	invalidateCache(c, post)
	realtime.DefaultHub.Publish(post.ThreadId.String(), realtime.Event{
		Type:     realtime.EventPostDeleted,
		ThreadID: post.ThreadId.String(),
		PostID:   post.Id.String(),
	})

	c.JSON(http.StatusOK, gin.H{
		"message": "Пост удалён",
		"post_id": post.Id,
	})
}

func invalidateCache(c *gin.Context, post models.Post) {
	if !cache.IsGlobalCacheReady() {
		return
	}

	ctx, cancel := context.WithTimeout(c.Request.Context(), 5*time.Second)
	defer cancel()

	forumCache := cache.GetGlobalForumCache()
	if err := forumCache.InvalidatePost(ctx, post.Id.String()); err != nil {
		c.Header("Cache-Warning", "Не удалось обновить кеш поста")
	}
	if err := forumCache.InvalidateThread(ctx, post.ThreadId.String()); err != nil {
		c.Header("Cache-Warning", "Не удалось обновить кеш треда")
	}
}
