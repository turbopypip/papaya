package getThreadRecommendations

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"os"
	"papaya-backend/internal/http-server/rbac"
	"papaya-backend/internal/storage"
	"papaya-backend/internal/storage/models"
	"strconv"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/gofrs/uuid"
)

const (
	statusReady             = "ready"
	statusModelNotReady     = "model_not_ready"
	statusNoRecommendations = "no_recommendations"
	defaultLimit            = 10
	maxLimit                = 50
	defaultServiceURL       = "http://localhost:8000"
	recommenderHTTPTimeout  = 30 * time.Second
)

type recommendationItem struct {
	Thread               models.Thread  `json:"thread"`
	Score                float64        `json:"score"`
	RecommendationSource string         `json:"recommendation_source"`
	ModelVersion         string         `json:"model_version"`
	GeneratedAt          string         `json:"generated_at"`
	RunID                string         `json:"run_id,omitempty"`
	GenerationID         string         `json:"generation_id"`
	Metadata             map[string]any `json:"metadata,omitempty"`
}

type recommenderService interface {
	RecommendThreads(ctx context.Context, userID string, limit int) (serviceRecommendationsResponse, error)
}

type serviceRecommendationsResponse struct {
	Status          string                      `json:"status"`
	Recommendations []serviceRecommendationItem `json:"recommendations"`
	ModelVersion    string                      `json:"model_version"`
	GeneratedAt     string                      `json:"generated_at"`
	RunID           string                      `json:"run_id"`
	GenerationID    string                      `json:"generation_id"`
	Metadata        map[string]any              `json:"metadata"`
}

type serviceRecommendationItem struct {
	ThreadID             string         `json:"thread_id"`
	Score                float64        `json:"score"`
	RecommendationSource string         `json:"recommendation_source"`
	ModelVersion         string         `json:"model_version"`
	RunID                string         `json:"run_id"`
	GenerationID         string         `json:"generation_id"`
	Metadata             map[string]any `json:"metadata"`
}

type httpRecommenderService struct {
	baseURL string
	client  *http.Client
}

var recommenderServiceFactory = func() recommenderService {
	return newHTTPRecommenderService(recommenderServiceURL())
}

func GetThreadRecommendations(c *gin.Context) {
	user, ok := rbac.CurrentUser(c)
	if !ok {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "Войдите в аккаунт"})
		return
	}

	limit := parseLimit(c.Query("limit"))
	serviceResponse, err := recommenderServiceFactory().RecommendThreads(c.Request.Context(), user.Id.String(), limit)
	if err != nil {
		c.JSON(http.StatusOK, emptyResponse(statusModelNotReady))
		return
	}
	if serviceResponse.Status == statusModelNotReady {
		c.JSON(http.StatusOK, emptyResponse(statusModelNotReady))
		return
	}
	if len(serviceResponse.Recommendations) == 0 {
		c.JSON(http.StatusOK, emptyResponse(statusNoRecommendations))
		return
	}

	threadIDs := make([]uuid.UUID, 0, len(serviceResponse.Recommendations))
	for _, value := range serviceResponse.Recommendations {
		threadID, err := uuid.FromString(value.ThreadID)
		if err != nil {
			continue
		}

		threadIDs = append(threadIDs, threadID)
	}

	if len(threadIDs) == 0 {
		c.JSON(http.StatusOK, emptyResponse(statusNoRecommendations))
		return
	}

	var threads []models.Thread
	if err := storage.DB.Preload("Author").Find(&threads, "id IN ?", threadIDs).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Не удалось загрузить рекомендованные треды"})
		return
	}

	threadsByID := make(map[string]models.Thread, len(threads))
	for _, thread := range threads {
		threadsByID[thread.Id.String()] = thread
	}

	items := make([]recommendationItem, 0, len(serviceResponse.Recommendations))
	for _, value := range serviceResponse.Recommendations {
		thread, ok := threadsByID[value.ThreadID]
		if !ok {
			continue
		}
		modelVersion := value.ModelVersion
		if modelVersion == "" {
			modelVersion = serviceResponse.ModelVersion
		}
		generationID := value.GenerationID
		if generationID == "" {
			generationID = serviceResponse.GenerationID
		}
		runID := value.RunID
		if runID == "" {
			runID = serviceResponse.RunID
		}

		items = append(items, recommendationItem{
			Thread:               thread,
			Score:                value.Score,
			RecommendationSource: normalizeRecommendationSource(value.RecommendationSource),
			ModelVersion:         modelVersion,
			GeneratedAt:          serviceResponse.GeneratedAt,
			RunID:                runID,
			GenerationID:         generationID,
			Metadata:             value.Metadata,
		})
	}

	if len(items) == 0 {
		c.JSON(http.StatusOK, emptyResponse(statusNoRecommendations))
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"status":          statusReady,
		"recommendations": items,
		"model_version":   serviceResponse.ModelVersion,
		"generated_at":    serviceResponse.GeneratedAt,
		"run_id":          serviceResponse.RunID,
		"generation_id":   serviceResponse.GenerationID,
		"metadata":        serviceResponse.Metadata,
	})
}

func newHTTPRecommenderService(baseURL string) httpRecommenderService {
	return httpRecommenderService{
		baseURL: strings.TrimRight(baseURL, "/"),
		client:  &http.Client{Timeout: recommenderHTTPTimeout},
	}
}

func (service httpRecommenderService) RecommendThreads(ctx context.Context, userID string, limit int) (serviceRecommendationsResponse, error) {
	body, err := json.Marshal(map[string]any{
		"user_id": userID,
		"limit":   limit,
	})
	if err != nil {
		return serviceRecommendationsResponse{}, err
	}
	request, err := http.NewRequestWithContext(ctx, http.MethodPost, service.baseURL+"/recommendations/threads", bytes.NewReader(body))
	if err != nil {
		return serviceRecommendationsResponse{}, err
	}
	request.Header.Set("Content-Type", "application/json")
	response, err := service.client.Do(request)
	if err != nil {
		return serviceRecommendationsResponse{}, err
	}
	defer response.Body.Close()
	if response.StatusCode >= http.StatusBadRequest {
		return serviceRecommendationsResponse{}, fmt.Errorf("recommender service returned status %d", response.StatusCode)
	}
	data, err := io.ReadAll(response.Body)
	if err != nil {
		return serviceRecommendationsResponse{}, err
	}
	var result serviceRecommendationsResponse
	if err := json.Unmarshal(data, &result); err != nil {
		return serviceRecommendationsResponse{}, err
	}
	if result.Status == "" {
		return serviceRecommendationsResponse{}, errors.New("recommender service response is missing status")
	}
	return result, nil
}

func recommenderServiceURL() string {
	value := strings.TrimSpace(os.Getenv("RECOMMENDER_SERVICE_URL"))
	if value == "" {
		return defaultServiceURL
	}
	return value
}

func normalizeRecommendationSource(source string) string {
	source = strings.TrimSpace(source)
	if source == "" {
		return "model"
	}
	return source
}

func parseLimit(value string) int {
	limit, err := strconv.Atoi(value)
	if err != nil || limit < 1 {
		return defaultLimit
	}
	if limit > maxLimit {
		return maxLimit
	}
	return limit
}

func emptyResponse(status string) gin.H {
	return gin.H{
		"status":          status,
		"recommendations": []recommendationItem{},
	}
}
