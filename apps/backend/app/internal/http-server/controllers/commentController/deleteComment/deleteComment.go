package deleteComment

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

func DeleteComment(c *gin.Context) {
	commentID, err := uuid.FromString(c.Param("id"))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Некорректный идентификатор комментария"})
		return
	}

	var comment models.Comment
	if err := storage.DB.First(&comment, "id = ?", commentID).Error; errors.Is(err, gorm.ErrRecordNotFound) {
		c.JSON(http.StatusNotFound, gin.H{"error": "Комментарий не найден"})
		return
	} else if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Не удалось получить комментарий"})
		return
	}

	if !rbac.Can(c, rbac.ResourceComments, rbac.ActionDelete, comment.UserId) {
		c.JSON(http.StatusForbidden, gin.H{"error": "У вас нет прав удалить этот комментарий"})
		return
	}

	var post models.Post
	if err := storage.DB.First(&post, "id = ?", comment.PostId).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Не удалось получить пост комментария"})
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
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Не удалось удалить комментарий"})
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
		"message":    "Комментарий удалён",
		"comment_id": comment.Id,
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
