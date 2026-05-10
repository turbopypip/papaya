package cache

import (
	"context"
	"fmt"
	"time"
)

// ForumCache предоставляет методы для кэширования данных форума
type ForumCache struct {
	cache Cache
}

// NewForumCache создает новый экземпляр ForumCache
func NewForumCache(cache Cache) *ForumCache {
	return &ForumCache{
		cache: cache,
	}
}

// Константы для TTL
const (
	UserCacheTTL     = 15 * time.Second
	PostCacheTTL     = 10 * time.Second
	ThreadCacheTTL   = 10 * time.Second
	CategoryCacheTTL = 1 * time.Second
)

// Префиксы для ключей
const (
	UserPrefix     = "user:"
	PostPrefix     = "post:"
	ThreadPrefix   = "thread:"
	CategoryPrefix = "category:"
	ViewsPrefix    = "views:"
)

// CacheUser кэширует данные пользователя
func (fc *ForumCache) CacheUser(ctx context.Context, userID string, userData interface{}) error {
	key := UserPrefix + userID
	return fc.cache.Set(ctx, key, userData, UserCacheTTL)
}

// GetUser получает данные пользователя из кэша
func (fc *ForumCache) GetUser(ctx context.Context, userID string, userData interface{}) error {
	key := UserPrefix + userID
	return fc.cache.Get(ctx, key, userData)
}

// CachePost кэширует данные поста
func (fc *ForumCache) CachePost(ctx context.Context, postID string, postData interface{}) error {
	key := PostPrefix + postID
	return fc.cache.Set(ctx, key, postData, PostCacheTTL)
}

// GetPost получает данные поста из кэша
func (fc *ForumCache) GetPost(ctx context.Context, postID string, postData interface{}) error {
	key := PostPrefix + postID
	return fc.cache.Get(ctx, key, postData)
}

// CacheThread кэширует данные темы
func (fc *ForumCache) CacheThread(ctx context.Context, threadID string, threadData interface{}) error {
	key := ThreadPrefix + threadID
	return fc.cache.Set(ctx, key, threadData, ThreadCacheTTL)
}

// GetThread получает данные темы из кэша
func (fc *ForumCache) GetThread(ctx context.Context, threadID string, threadData interface{}) error {
	key := ThreadPrefix + threadID
	return fc.cache.Get(ctx, key, threadData)
}

// IncrementViews увеличивает счетчик просмотров
func (fc *ForumCache) IncrementViews(ctx context.Context, entityType, entityID string) (int64, error) {
	key := fmt.Sprintf("%s%s:%s", ViewsPrefix, entityType, entityID)
	return fc.cache.Increment(ctx, key)
}

// InvalidateUser удаляет данные пользователя из кэша
func (fc *ForumCache) InvalidateUser(ctx context.Context, userID string) error {
	key := UserPrefix + userID
	return fc.cache.Delete(ctx, key)
}

// InvalidatePost удаляет данные поста из кэша
func (fc *ForumCache) InvalidatePost(ctx context.Context, postID string) error {
	key := PostPrefix + postID
	return fc.cache.Delete(ctx, key)
}

// InvalidateThread удаляет данные темы из кэша
func (fc *ForumCache) InvalidateThread(ctx context.Context, threadID string) error {
	key := ThreadPrefix + threadID
	return fc.cache.Delete(ctx, key)
}
