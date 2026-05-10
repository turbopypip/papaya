package cache

import (
	"sync"
)

// Глобальные экземпляры кэшей
var (
	globalForumCache *ForumCache
	globalRedisCache Cache
	globalMutex      sync.RWMutex
)

// SetGlobalCaches устанавливает глобальные экземпляры кэшей
func SetGlobalCaches(redisCache Cache, forumCache *ForumCache) {
	globalMutex.Lock()
	defer globalMutex.Unlock()
	globalRedisCache = redisCache
	globalForumCache = forumCache
}

// SetGlobalForumCache устанавливает глобальный экземпляр кэша
func SetGlobalForumCache(cache *ForumCache) {
	globalMutex.Lock()
	defer globalMutex.Unlock()
	globalForumCache = cache
}

// GetGlobalForumCache возвращает глобальный экземпляр кэша
func GetGlobalForumCache() *ForumCache {
	globalMutex.RLock()
	defer globalMutex.RUnlock()
	return globalForumCache
}

// GetGlobalRedisCache возвращает глобальный экземпляр Redis кэша
func GetGlobalRedisCache() Cache {
	globalMutex.RLock()
	defer globalMutex.RUnlock()
	return globalRedisCache
}

// IsGlobalCacheReady проверяет, инициализирован ли глобальный кэш
func IsGlobalCacheReady() bool {
	globalMutex.RLock()
	defer globalMutex.RUnlock()
	return globalForumCache != nil && globalRedisCache != nil
}
