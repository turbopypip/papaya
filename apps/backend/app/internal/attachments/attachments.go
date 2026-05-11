package attachments

import (
	"errors"
	"fmt"
	"mime"
	"mime/multipart"
	"net/http"
	"os"
	"path/filepath"
	"strings"

	"github.com/gin-gonic/gin"
	"github.com/gofrs/uuid"
	"gorm.io/gorm"

	"papaya-backend/internal/storage/models"
)

const (
	OwnerTypeThread  = "thread"
	OwnerTypePost    = "post"
	OwnerTypeComment = "comment"

	MaxFilesPerOwner = 5
	MaxFileSize      = 10 * 1024 * 1024
)

var allowedContentTypes = map[string]struct{}{
	"image/jpeg":               {},
	"image/png":                {},
	"image/gif":                {},
	"image/webp":               {},
	"application/pdf":          {},
	"application/json":         {},
	"application/x-ipynb+json": {},
	"text/plain":               {},
	"application/msword":       {},
	"application/vnd.openxmlformats-officedocument.wordprocessingml.document": {},
	"application/vnd.ms-excel": {},
	"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":         {},
	"application/vnd.ms-powerpoint":                                             {},
	"application/vnd.openxmlformats-officedocument.presentationml.presentation": {},
	"application/zip": {},
}

type ValidationError struct {
	Message string
}

func (e ValidationError) Error() string {
	return e.Message
}

func IsValidationError(err error) bool {
	var validationError ValidationError
	return errors.As(err, &validationError)
}

func UploadDir() string {
	if uploadDir := strings.TrimSpace(os.Getenv("UPLOADS_PATH")); uploadDir != "" {
		return uploadDir
	}

	return "uploads"
}

func PublicURL(storageKey string) string {
	return "/uploads/" + storageKey
}

func FilesFromRequest(c *gin.Context) ([]*multipart.FileHeader, error) {
	form, err := c.MultipartForm()
	if err != nil {
		if errors.Is(err, http.ErrNotMultipart) {
			return nil, nil
		}

		return nil, err
	}

	files := make([]*multipart.FileHeader, 0)
	for _, field := range []string{"attachments", "files", "file"} {
		files = append(files, form.File[field]...)
	}

	if len(files) > MaxFilesPerOwner {
		return nil, ValidationError{Message: fmt.Sprintf("maximum %d attachments are allowed", MaxFilesPerOwner)}
	}

	return files, nil
}

func CreateFromRequest(c *gin.Context, tx *gorm.DB, ownerType string, ownerID uuid.UUID, userID uuid.UUID) ([]models.Attachment, []string, error) {
	files, err := FilesFromRequest(c)
	if err != nil {
		return nil, nil, err
	}
	if len(files) == 0 {
		return []models.Attachment{}, nil, nil
	}

	var existingCount int64
	if err := tx.Model(&models.Attachment{}).
		Where("owner_type = ? AND owner_id = ?", ownerType, ownerID).
		Count(&existingCount).Error; err != nil {
		return nil, nil, err
	}
	if existingCount+int64(len(files)) > MaxFilesPerOwner {
		return nil, nil, ValidationError{Message: fmt.Sprintf("maximum %d attachments are allowed", MaxFilesPerOwner)}
	}

	uploadDir := UploadDir()
	if err := os.MkdirAll(uploadDir, 0755); err != nil {
		return nil, nil, err
	}

	created := make([]models.Attachment, 0, len(files))
	savedPaths := make([]string, 0, len(files))

	for _, file := range files {
		contentType, err := validateFile(file)
		if err != nil {
			return created, savedPaths, err
		}

		attachmentID, err := uuid.NewV6()
		if err != nil {
			return created, savedPaths, err
		}

		extension := strings.ToLower(filepath.Ext(file.Filename))
		storageKey := attachmentID.String() + extension
		diskPath := filepath.Join(uploadDir, storageKey)

		if err := c.SaveUploadedFile(file, diskPath); err != nil {
			return created, savedPaths, err
		}
		savedPaths = append(savedPaths, diskPath)

		attachment := models.Attachment{
			Id:          attachmentID,
			Url:         PublicURL(storageKey),
			FileName:    filepath.Base(file.Filename),
			ContentType: contentType,
			Size:        file.Size,
			StorageKey:  storageKey,
			OwnerType:   ownerType,
			OwnerId:     ownerID,
			UserId:      userID,
		}

		if err := tx.Create(&attachment).Error; err != nil {
			return created, savedPaths, err
		}

		created = append(created, attachment)
	}

	return created, savedPaths, nil
}

func CleanupFiles(paths []string) {
	for _, path := range paths {
		_ = os.Remove(path)
	}
}

func AttachToThread(db *gorm.DB, thread *models.Thread) error {
	attachmentsByOwner, err := MapByOwner(db, OwnerTypeThread, []uuid.UUID{thread.Id})
	if err != nil {
		return err
	}

	thread.Attachments = attachmentsByOwner[thread.Id]
	return nil
}

func AttachToThreads(db *gorm.DB, threads []models.Thread) error {
	ids := make([]uuid.UUID, 0, len(threads))
	for _, thread := range threads {
		ids = append(ids, thread.Id)
	}

	attachmentsByOwner, err := MapByOwner(db, OwnerTypeThread, ids)
	if err != nil {
		return err
	}

	for i := range threads {
		threads[i].Attachments = attachmentsByOwner[threads[i].Id]
	}

	return nil
}

func AttachToPosts(db *gorm.DB, posts []models.Post) error {
	ids := make([]uuid.UUID, 0, len(posts))
	for _, post := range posts {
		ids = append(ids, post.Id)
	}

	attachmentsByOwner, err := MapByOwner(db, OwnerTypePost, ids)
	if err != nil {
		return err
	}

	for i := range posts {
		posts[i].Attachments = attachmentsByOwner[posts[i].Id]
	}

	return nil
}

func AttachToComments(db *gorm.DB, comments []models.Comment) error {
	ids := make([]uuid.UUID, 0, len(comments))
	for _, comment := range comments {
		ids = append(ids, comment.Id)
	}

	attachmentsByOwner, err := MapByOwner(db, OwnerTypeComment, ids)
	if err != nil {
		return err
	}

	for i := range comments {
		comments[i].Attachments = attachmentsByOwner[comments[i].Id]
	}

	return nil
}

func MapByOwner(db *gorm.DB, ownerType string, ownerIDs []uuid.UUID) (map[uuid.UUID][]models.Attachment, error) {
	result := make(map[uuid.UUID][]models.Attachment, len(ownerIDs))
	if len(ownerIDs) == 0 {
		return result, nil
	}

	var found []models.Attachment
	if err := db.
		Where("owner_type = ? AND owner_id IN ?", ownerType, ownerIDs).
		Order("created_at ASC").
		Find(&found).Error; err != nil {
		return nil, err
	}

	for _, attachment := range found {
		result[attachment.OwnerId] = append(result[attachment.OwnerId], attachment)
	}

	return result, nil
}

func validateFile(file *multipart.FileHeader) (string, error) {
	if file.Size <= 0 {
		return "", ValidationError{Message: "empty attachments are not allowed"}
	}
	if file.Size > MaxFileSize {
		return "", ValidationError{Message: fmt.Sprintf("%s exceeds the %d MB attachment limit", file.Filename, MaxFileSize/1024/1024)}
	}

	contentType := normalizeContentType(file.Header.Get("Content-Type"))
	if contentType == "" || contentType == "application/octet-stream" {
		detectedContentType, err := detectContentType(file)
		if err != nil {
			return "", err
		}
		contentType = normalizeContentType(detectedContentType)
	}
	if isNotebookFile(file.Filename, contentType) {
		return "application/x-ipynb+json", nil
	}

	if _, ok := allowedContentTypes[contentType]; !ok {
		return "", ValidationError{Message: fmt.Sprintf("%s has unsupported content type %s", file.Filename, contentType)}
	}

	return contentType, nil
}

func normalizeContentType(contentType string) string {
	contentType = strings.TrimSpace(contentType)
	if contentType == "" {
		return ""
	}

	mediaType, _, err := mime.ParseMediaType(contentType)
	if err != nil {
		return strings.ToLower(contentType)
	}

	return strings.ToLower(mediaType)
}

func isNotebookFile(filename string, contentType string) bool {
	if strings.ToLower(filepath.Ext(filename)) != ".ipynb" {
		return false
	}

	switch contentType {
	case "application/x-ipynb+json", "application/json", "text/plain":
		return true
	default:
		return false
	}
}

func detectContentType(file *multipart.FileHeader) (string, error) {
	src, err := file.Open()
	if err != nil {
		return "", err
	}
	defer src.Close()

	buffer := make([]byte, 512)
	readBytes, err := src.Read(buffer)
	if err != nil && readBytes == 0 {
		return "", err
	}

	return http.DetectContentType(buffer[:readBytes]), nil
}
