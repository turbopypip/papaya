package cache

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"papaya-backend/internal/config"

	"github.com/redis/go-redis/v9"
)

type RedisCache struct {
	client *redis.Client
}

// NewRedisCache создает новый экземпляр Redis кэша
func NewRedisCache(cfg config.RedisConfig) (*RedisCache, error) {
	client := redis.NewClient(&redis.Options{
		Addr:     cfg.Address,
		Password: cfg.Password,
		DB:       cfg.DB,
	})

	// Проверяем подключение
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := client.Ping(ctx).Err(); err != nil {
		return nil, fmt.Errorf("failed to connect to Redis: %w", err)
	}

	return &RedisCache{
		client: client,
	}, nil
}

// Set сохраняет значение в кэш с указанным TTL
func (r *RedisCache) Set(ctx context.Context, key string, value interface{}, ttl time.Duration) error {
	data, err := json.Marshal(value)
	if err != nil {
		return fmt.Errorf("failed to marshal value: %w", err)
	}

	return r.client.Set(ctx, key, data, ttl).Err()
}

// Get получает значение из кэша
func (r *RedisCache) Get(ctx context.Context, key string, dest interface{}) error {
	data, err := r.client.Get(ctx, key).Bytes()
	if err != nil {
		if err == redis.Nil {
			return ErrCacheMiss
		}
		return fmt.Errorf("failed to get value from cache: %w", err)
	}

	if err := json.Unmarshal(data, dest); err != nil {
		return fmt.Errorf("failed to unmarshal value: %w", err)
	}

	return nil
}

// Delete удаляет значение из кэша
func (r *RedisCache) Delete(ctx context.Context, key string) error {
	return r.client.Del(ctx, key).Err()
}

// Exists проверяет существование ключа
func (r *RedisCache) Exists(ctx context.Context, key string) (bool, error) {
	result := r.client.Exists(ctx, key)
	if err := result.Err(); err != nil {
		return false, fmt.Errorf("failed to check if key exists: %w", err)
	}
	return result.Val() > 0, nil
}

// SetNX устанавливает значение только если ключ не существует
func (r *RedisCache) SetNX(ctx context.Context, key string, value interface{}, ttl time.Duration) (bool, error) {
	data, err := json.Marshal(value)
	if err != nil {
		return false, fmt.Errorf("failed to marshal value: %w", err)
	}

	return r.client.SetNX(ctx, key, data, ttl).Result()
}

// Increment увеличивает числовое значение
func (r *RedisCache) Increment(ctx context.Context, key string) (int64, error) {
	return r.client.Incr(ctx, key).Result()
}

// Decrement уменьшает числовое значение
func (r *RedisCache) Decrement(ctx context.Context, key string) (int64, error) {
	return r.client.Decr(ctx, key).Result()
}

// Expire устанавливает TTL для существующего ключа
func (r *RedisCache) Expire(ctx context.Context, key string, ttl time.Duration) error {
	return r.client.Expire(ctx, key, ttl).Err()
}

// Close закрывает соединение с Redis
func (r *RedisCache) Close() error {
	return r.client.Close()
}

// InitRedis инициализирует Redis кэш и устанавливает глобальный форумный кэш
func InitRedis(cfg config.RedisConfig) (func(), error) {
	// Инициализируем Redis кэш
	redisCache, err := NewRedisCache(cfg)
	if err != nil {
		return nil, fmt.Errorf("failed to initialize Redis cache: %w", err)
	}

	// Создаем форумный кэш
	forumCache := NewForumCache(redisCache)

	// Устанавливаем глобальные кэши для доступа из контроллеров и middleware
	SetGlobalCaches(redisCache, forumCache)

	// Возвращаем функцию для закрытия соединения
	cleanup := func() {
		redisCache.Close()
	}

	return cleanup, nil
}
