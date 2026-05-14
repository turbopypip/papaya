package likeState

import (
	"testing"

	"github.com/gofrs/uuid"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"

	"papaya-backend/internal/storage"
	"papaya-backend/internal/storage/models"
)

func TestLoadSeparatesLikedByMePerUserAndSharesCount(t *testing.T) {
	originalDB := storage.DB
	t.Cleanup(func() {
		storage.DB = originalDB
	})

	db, err := gorm.Open(sqlite.Open("file::memory:?cache=shared"), &gorm.Config{})
	if err != nil {
		t.Fatalf("open test db: %v", err)
	}
	if err := db.AutoMigrate(&models.Like{}); err != nil {
		t.Fatalf("migrate test db: %v", err)
	}
	storage.DB = db

	likableID := uuid.Must(uuid.NewV4())
	firstUserID := uuid.Must(uuid.NewV4())
	secondUserID := uuid.Must(uuid.NewV4())

	firstLike := models.Like{
		Id:          uuid.Must(uuid.NewV4()),
		UserId:      firstUserID,
		LikableID:   likableID,
		LikableType: models.LikablePost,
	}
	if err := db.Create(&firstLike).Error; err != nil {
		t.Fatalf("create first like: %v", err)
	}

	firstState, err := Load(likableID, models.LikablePost, firstUserID)
	if err != nil {
		t.Fatalf("load first user state: %v", err)
	}
	if firstState.Count != 1 {
		t.Fatalf("expected shared count 1 for first user, got %d", firstState.Count)
	}
	if !firstState.LikedByMe {
		t.Fatal("expected first user to see liked_by_me=true")
	}

	secondState, err := Load(likableID, models.LikablePost, secondUserID)
	if err != nil {
		t.Fatalf("load second user state: %v", err)
	}
	if secondState.Count != 1 {
		t.Fatalf("expected shared count 1 for second user, got %d", secondState.Count)
	}
	if secondState.LikedByMe {
		t.Fatal("expected second user to see liked_by_me=false")
	}

	secondLike := models.Like{
		Id:          uuid.Must(uuid.NewV4()),
		UserId:      secondUserID,
		LikableID:   likableID,
		LikableType: models.LikablePost,
	}
	if err := db.Create(&secondLike).Error; err != nil {
		t.Fatalf("create second like: %v", err)
	}

	secondStateAfterLike, err := Load(likableID, models.LikablePost, secondUserID)
	if err != nil {
		t.Fatalf("load second user state after like: %v", err)
	}
	if secondStateAfterLike.Count != 2 {
		t.Fatalf("expected shared count 2 after second like, got %d", secondStateAfterLike.Count)
	}
	if !secondStateAfterLike.LikedByMe {
		t.Fatal("expected second user to see liked_by_me=true after liking")
	}
}
