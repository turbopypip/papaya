package getThreadRecommendations

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"papaya-backend/internal/storage"
	"papaya-backend/internal/storage/models"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/gofrs/uuid"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
)

type failingRecommendationService struct{}

func (failingRecommendationService) RecommendThreads(context.Context, string, int) (serviceRecommendationsResponse, error) {
	return serviceRecommendationsResponse{}, errors.New("service unavailable")
}

type successfulRecommendationService struct {
	response serviceRecommendationsResponse
}

func (service successfulRecommendationService) RecommendThreads(context.Context, string, int) (serviceRecommendationsResponse, error) {
	return service.response, nil
}

func setRecommendationServiceForTest(service recommenderService) func() {
	previous := recommenderServiceFactory
	recommenderServiceFactory = func() recommenderService {
		return service
	}
	return func() {
		recommenderServiceFactory = previous
	}
}

func TestParseLimitBoundsRecommendationRequests(t *testing.T) {
	if got := parseLimit(""); got != defaultLimit {
		t.Fatalf("expected default limit, got %d", got)
	}
	if got := parseLimit("0"); got != defaultLimit {
		t.Fatalf("expected default limit for zero, got %d", got)
	}
	if got := parseLimit("500"); got != maxLimit {
		t.Fatalf("expected max limit, got %d", got)
	}
	if got := parseLimit("7"); got != 7 {
		t.Fatalf("expected explicit limit, got %d", got)
	}
}

func TestGetThreadRecommendationsRequiresAuthenticatedUser(t *testing.T) {
	gin.SetMode(gin.TestMode)
	recorder := httptest.NewRecorder()
	context, _ := gin.CreateTestContext(recorder)
	context.Request = httptest.NewRequest(http.MethodGet, "/api/v1/recommendations/threads", nil)

	GetThreadRecommendations(context)

	if recorder.Code != http.StatusUnauthorized {
		t.Fatalf("expected 401, got %d", recorder.Code)
	}
}

func TestGetThreadRecommendationsReturnsModelNotReadyWhenServiceUnavailable(t *testing.T) {
	gin.SetMode(gin.TestMode)
	defer setRecommendationServiceForTest(failingRecommendationService{})()
	recorder := httptest.NewRecorder()
	context, _ := gin.CreateTestContext(recorder)
	context.Request = httptest.NewRequest(http.MethodGet, "/api/v1/recommendations/threads", nil)
	context.Set("user", models.User{Id: uuid.Must(uuid.NewV4())})

	GetThreadRecommendations(context)

	if recorder.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", recorder.Code)
	}
	var body map[string]interface{}
	if err := json.Unmarshal(recorder.Body.Bytes(), &body); err != nil {
		t.Fatalf("failed to decode body: %v", err)
	}
	if body["status"] != statusModelNotReady {
		t.Fatalf("expected status %q, got %q", statusModelNotReady, body["status"])
	}
}

func TestGetThreadRecommendationsReturnsNoRecommendationsForEmptyCatalog(t *testing.T) {
	gin.SetMode(gin.TestMode)
	defer setRecommendationServiceForTest(successfulRecommendationService{
		response: serviceRecommendationsResponse{
			Status:          statusNoRecommendations,
			Recommendations: []serviceRecommendationItem{},
			ModelVersion:    "winner-v1",
			GeneratedAt:     "2026-05-20T12:00:00Z",
			GenerationID:    "generation-1",
		},
	})()
	recorder := httptest.NewRecorder()
	context, _ := gin.CreateTestContext(recorder)
	context.Request = httptest.NewRequest(http.MethodGet, "/api/v1/recommendations/threads", nil)
	context.Set("user", models.User{Id: uuid.Must(uuid.NewV4())})

	GetThreadRecommendations(context)

	if recorder.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", recorder.Code)
	}
	var body struct {
		Status          string               `json:"status"`
		Recommendations []recommendationItem `json:"recommendations"`
	}
	if err := json.Unmarshal(recorder.Body.Bytes(), &body); err != nil {
		t.Fatalf("failed to decode body: %v", err)
	}
	if body.Status != statusNoRecommendations {
		t.Fatalf("expected status %q, got %q", statusNoRecommendations, body.Status)
	}
	if len(body.Recommendations) != 0 {
		t.Fatalf("expected empty recommendations, got %d", len(body.Recommendations))
	}
}

func TestGetThreadRecommendationsReturnsServiceScoresWithThreadDetails(t *testing.T) {
	gin.SetMode(gin.TestMode)
	db := openRecommendationTestDB(t)
	previousDB := storage.DB
	storage.DB = db
	defer func() { storage.DB = previousDB }()

	userID := uuid.Must(uuid.NewV4())
	authorID := uuid.Must(uuid.NewV4())
	threadID := uuid.Must(uuid.NewV4())
	if err := db.Create(&models.User{Id: authorID, Username: "author"}).Error; err != nil {
		t.Fatalf("failed to create author: %v", err)
	}
	if err := db.Create(&models.Thread{Id: threadID, Title: "Winner path", UserId: authorID}).Error; err != nil {
		t.Fatalf("failed to create thread: %v", err)
	}

	defer setRecommendationServiceForTest(successfulRecommendationService{
		response: serviceRecommendationsResponse{
			Status:       statusReady,
			ModelVersion: "winner-v1",
			GeneratedAt:  "2026-05-20T12:00:00Z",
			RunID:        "run-1",
			GenerationID: "generation-1",
			Metadata:     map[string]any{"model_type": "entity_feature_sgd"},
			Recommendations: []serviceRecommendationItem{
				{
					ThreadID:             threadID.String(),
					Score:                0.87,
					RecommendationSource: "model",
					ModelVersion:         "winner-v1",
					RunID:                "run-1",
					GenerationID:         "generation-1",
				},
			},
		},
	})()

	recorder := httptest.NewRecorder()
	context, _ := gin.CreateTestContext(recorder)
	context.Request = httptest.NewRequest(http.MethodGet, "/api/v1/recommendations/threads?limit=5", nil)
	context.Set("user", models.User{Id: userID})

	GetThreadRecommendations(context)

	if recorder.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d: %s", recorder.Code, recorder.Body.String())
	}
	var body struct {
		Status          string               `json:"status"`
		ModelVersion    string               `json:"model_version"`
		RunID           string               `json:"run_id"`
		GenerationID    string               `json:"generation_id"`
		Recommendations []recommendationItem `json:"recommendations"`
	}
	if err := json.Unmarshal(recorder.Body.Bytes(), &body); err != nil {
		t.Fatalf("failed to decode body: %v", err)
	}
	if body.Status != statusReady {
		t.Fatalf("expected status ready, got %q", body.Status)
	}
	if body.ModelVersion != "winner-v1" || body.RunID != "run-1" || body.GenerationID != "generation-1" {
		t.Fatalf("missing recommendation metadata: %+v", body)
	}
	if len(body.Recommendations) != 1 {
		t.Fatalf("expected 1 recommendation, got %d", len(body.Recommendations))
	}
	item := body.Recommendations[0]
	if item.Thread.Id != threadID || item.Thread.Author.Username != "author" {
		t.Fatalf("expected PostgreSQL thread details, got %+v", item.Thread)
	}
	if item.Score != 0.87 || item.RecommendationSource != "model" || item.ModelVersion != "winner-v1" || item.RunID != "run-1" || item.GenerationID != "generation-1" {
		t.Fatalf("unexpected recommendation item: %+v", item)
	}
}

func openRecommendationTestDB(t *testing.T) *gorm.DB {
	t.Helper()
	db, err := gorm.Open(sqlite.Open(":memory:"), &gorm.Config{})
	if err != nil {
		t.Fatalf("failed to open sqlite db: %v", err)
	}
	if err := db.AutoMigrate(&models.User{}, &models.Thread{}); err != nil {
		t.Fatalf("failed to migrate sqlite db: %v", err)
	}
	return db
}
