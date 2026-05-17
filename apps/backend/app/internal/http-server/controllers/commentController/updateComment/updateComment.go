package updateComment

import (
	"context"
	"errors"
	"net/http"
	"papaya-backend/internal/attachments"
	"papaya-backend/internal/cache"
	"papaya-backend/internal/forumvalidation"
	"papaya-backend/internal/http-server/rbac"
	"papaya-backend/internal/realtime"
	"papaya-backend/internal/storage"
	"papaya-backend/internal/storage/models"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/gofrs/uuid"
	"gorm.io/gorm"
)

type updateCommentBody struct {
	Content          string
	KeepAttachmentID []uuid.UUID
	HasKeepList      bool
}

func UpdateComment(c *gin.Context) {
	commentID, err := uuid.FromString(c.Param("id"))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid comment id"})
		return
	}

	body, err := bindBody(c)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	if err := forumvalidation.ValidateCommentContent(body.Content); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
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

	if !rbac.Can(c, rbac.ResourceComments, rbac.ActionUpdate, comment.UserId) {
		c.JSON(http.StatusForbidden, gin.H{"error": "You cannot edit this comment"})
		return
	}

	var post models.Post
	if err := storage.DB.First(&post, "id = ?", comment.PostId).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to retrieve comment post"})
		return
	}

	var savedFiles []string
	var removedFiles []string
	err = storage.DB.Transaction(func(tx *gorm.DB) error {
		comment.Content = body.Content
		if err := tx.Save(&comment).Error; err != nil {
			return err
		}

		if body.HasKeepList {
			paths, err := attachments.DeleteRemovedForOwner(
				tx,
				attachments.OwnerTypeComment,
				comment.Id,
				body.KeepAttachmentID,
			)
			if err != nil {
				return err
			}
			removedFiles = append(removedFiles, paths...)
		}

		createdAttachments, paths, err := attachments.CreateFromRequest(
			c,
			tx,
			attachments.OwnerTypeComment,
			comment.Id,
			userData.Id,
		)
		savedFiles = append(savedFiles, paths...)
		if err != nil {
			return err
		}

		comment.Attachments = createdAttachments
		return nil
	})
	if err != nil {
		attachments.CleanupFiles(savedFiles)
		if attachments.IsValidationError(err) {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to update comment"})
		return
	}
	attachments.CleanupFiles(removedFiles)

	if err := storage.DB.Preload("Author").First(&comment, "id = ?", comment.Id).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to retrieve comment"})
		return
	}

	comments := []models.Comment{comment}
	if err := attachments.AttachToComments(storage.DB, comments); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to retrieve comment attachments"})
		return
	}
	comment = comments[0]

	invalidateCache(c, post)
	realtime.DefaultHub.Publish(post.ThreadId.String(), realtime.Event{
		Type:      realtime.EventCommentUpdated,
		ThreadID:  post.ThreadId.String(),
		PostID:    comment.PostId.String(),
		CommentID: comment.Id.String(),
	})

	c.JSON(http.StatusOK, gin.H{
		"message": "updated comment",
		"comment": comment,
	})
}

func bindBody(c *gin.Context) (updateCommentBody, error) {
	var body updateCommentBody

	if strings.HasPrefix(c.GetHeader("Content-Type"), "multipart/form-data") {
		body.Content = c.PostForm("content")
		form, err := c.MultipartForm()
		if err != nil && !errors.Is(err, http.ErrNotMultipart) {
			return body, err
		}
		if form != nil {
			rawIDs, ok := form.Value["keep_attachment_ids"]
			body.HasKeepList = ok || c.PostForm("replace_attachments") == "true"
			for _, rawID := range rawIDs {
				id, err := uuid.FromString(rawID)
				if err != nil {
					return body, errors.New("Invalid attachment id")
				}
				body.KeepAttachmentID = append(body.KeepAttachmentID, id)
			}
		}
		return body, nil
	}

	var jsonBody struct {
		Content          string    `json:"content"`
		KeepAttachmentID *[]string `json:"keep_attachment_ids"`
	}
	if err := c.ShouldBindJSON(&jsonBody); err != nil {
		return body, err
	}

	body.Content = jsonBody.Content
	body.HasKeepList = jsonBody.KeepAttachmentID != nil
	if jsonBody.KeepAttachmentID != nil {
		for _, rawID := range *jsonBody.KeepAttachmentID {
			id, err := uuid.FromString(rawID)
			if err != nil {
				return body, errors.New("Invalid attachment id")
			}
			body.KeepAttachmentID = append(body.KeepAttachmentID, id)
		}
	}

	return body, nil
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
