package updateThread

import (
	"context"
	"errors"
	"net/http"
	"papaya-backend/internal/attachments"
	"papaya-backend/internal/cache"
	"papaya-backend/internal/forumvalidation"
	"papaya-backend/internal/realtime"
	"papaya-backend/internal/storage"
	"papaya-backend/internal/storage/models"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/gofrs/uuid"
	"gorm.io/gorm"
)

type updateThreadBody struct {
	Title             string
	Categories        []string
	KeepAttachmentIDs []uuid.UUID
	HasKeepList       bool
}

func UpdateThread(c *gin.Context) {
	threadID, err := uuid.FromString(c.Param("id"))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid thread id"})
		return
	}

	body, err := bindBody(c)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	categories, err := forumvalidation.ValidateThread(body.Title, body.Categories)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	user, _ := c.Get("user")
	userData := user.(models.User)

	var thread models.Thread
	if err := storage.DB.First(&thread, "id = ?", threadID).Error; errors.Is(err, gorm.ErrRecordNotFound) {
		c.JSON(http.StatusNotFound, gin.H{"error": "Thread not found"})
		return
	} else if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to retrieve thread"})
		return
	}

	if !canUpdateThread(userData, thread) {
		c.JSON(http.StatusForbidden, gin.H{"error": "You cannot edit this thread"})
		return
	}

	var savedFiles []string
	var removedFiles []string
	err = storage.DB.Transaction(func(tx *gorm.DB) error {
		thread.Title = strings.TrimSpace(body.Title)
		thread.Categories = categories
		if err := tx.Save(&thread).Error; err != nil {
			return err
		}

		if body.HasKeepList {
			paths, err := attachments.DeleteRemovedForOwner(
				tx,
				attachments.OwnerTypeThread,
				thread.Id,
				body.KeepAttachmentIDs,
			)
			if err != nil {
				return err
			}
			removedFiles = append(removedFiles, paths...)
		}

		createdAttachments, paths, err := attachments.CreateFromRequest(
			c,
			tx,
			attachments.OwnerTypeThread,
			thread.Id,
			userData.Id,
		)
		savedFiles = append(savedFiles, paths...)
		if err != nil {
			return err
		}

		thread.Attachments = createdAttachments
		return nil
	})
	if err != nil {
		attachments.CleanupFiles(savedFiles)
		if attachments.IsValidationError(err) {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to update thread"})
		return
	}
	attachments.CleanupFiles(removedFiles)

	if err := attachments.AttachToThread(storage.DB, &thread); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to retrieve thread attachments"})
		return
	}

	invalidateCache(c, thread)
	realtime.DefaultHub.Publish(thread.Id.String(), realtime.Event{
		Type:     realtime.EventThreadUpdated,
		ThreadID: thread.Id.String(),
	})

	c.JSON(http.StatusOK, gin.H{
		"message": "updated thread",
		"thread":  thread,
	})
}

func bindBody(c *gin.Context) (updateThreadBody, error) {
	var body updateThreadBody

	if strings.HasPrefix(c.GetHeader("Content-Type"), "multipart/form-data") {
		body.Title = c.PostForm("title")
		body.Categories = c.PostFormArray("categories")
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
				body.KeepAttachmentIDs = append(body.KeepAttachmentIDs, id)
			}
		}
		return body, nil
	}

	var jsonBody struct {
		Title             string    `json:"title"`
		Categories        []string  `json:"categories"`
		KeepAttachmentIDs *[]string `json:"keep_attachment_ids"`
	}
	if err := c.ShouldBindJSON(&jsonBody); err != nil {
		return body, err
	}

	body.Title = jsonBody.Title
	body.Categories = jsonBody.Categories
	body.HasKeepList = jsonBody.KeepAttachmentIDs != nil
	if jsonBody.KeepAttachmentIDs != nil {
		for _, rawID := range *jsonBody.KeepAttachmentIDs {
			id, err := uuid.FromString(rawID)
			if err != nil {
				return body, errors.New("Invalid attachment id")
			}
			body.KeepAttachmentIDs = append(body.KeepAttachmentIDs, id)
		}
	}

	return body, nil
}

func canUpdateThread(user models.User, thread models.Thread) bool {
	var role models.Role
	if err := storage.DB.First(&role, "id = ?", user.RoleId).Error; err != nil {
		return thread.UserId == user.Id
	}

	if thread.UserId == user.Id && role.Permissions.Threads.UpdateOwn {
		return true
	}

	return role.Permissions.Threads.UpdateAny
}

func invalidateCache(c *gin.Context, thread models.Thread) {
	if !cache.IsGlobalCacheReady() {
		return
	}

	ctx, cancel := context.WithTimeout(c.Request.Context(), 5*time.Second)
	defer cancel()

	forumCache := cache.GetGlobalForumCache()
	if err := forumCache.InvalidateThread(ctx, thread.Id.String()); err != nil {
		c.Header("Cache-Warning", "Failed to invalidate thread cache")
	}
}
