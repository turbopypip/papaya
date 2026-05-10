package cache

import (
	"bytes"
	"context"
	"crypto/md5"
	"encoding/hex"
	"fmt"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
)

// ResponseWriter для перехвата ответа
type responseWriter struct {
	gin.ResponseWriter
	body *bytes.Buffer
}

func (w *responseWriter) Write(b []byte) (int, error) {
	w.body.Write(b)
	return w.ResponseWriter.Write(b)
}

// CacheMiddleware создает middleware для кэширования GET запросов
func CacheMiddleware(cache Cache, ttl time.Duration) gin.HandlerFunc {
	return func(c *gin.Context) {
		// Проверяем что кэш инициализирован
		if cache == nil {
			c.Next()
			return
		}

		// Кэшируем только GET запросы
		if c.Request.Method != http.MethodGet {
			c.Next()
			return
		}

		// Генерируем ключ кэша на основе URL и query параметров
		key := generateCacheKey(c.Request.URL.Path, c.Request.URL.RawQuery)

		// Пытаемся получить из кэша
		var cachedResponse struct {
			Status  int               `json:"status"`
			Headers map[string]string `json:"headers"`
			Body    []byte            `json:"body"`
		}

		ctx := context.Background()
		err := cache.Get(ctx, key, &cachedResponse)
		if err == nil {
			// Восстанавливаем заголовки
			for k, v := range cachedResponse.Headers {
				c.Header(k, v)
			}
			// Отправляем кэшированный ответ
			c.Data(cachedResponse.Status, c.ContentType(), cachedResponse.Body)
			c.Abort()
			return
		}

		// Создаем custom writer для перехвата ответа
		w := &responseWriter{
			ResponseWriter: c.Writer,
			body:           bytes.NewBuffer(nil),
		}
		c.Writer = w

		// Обрабатываем запрос
		c.Next()

		// Кэшируем только успешные ответы
		if c.Writer.Status() >= 200 && c.Writer.Status() < 300 {
			responseToCache := struct {
				Status  int               `json:"status"`
				Headers map[string]string `json:"headers"`
				Body    []byte            `json:"body"`
			}{
				Status:  c.Writer.Status(),
				Headers: make(map[string]string),
				Body:    w.body.Bytes(),
			}

			// Сохраняем важные заголовки
			for k, v := range c.Writer.Header() {
				if len(v) > 0 {
					responseToCache.Headers[k] = v[0]
				}
			}

			// Сохраняем в кэш
			cache.Set(ctx, key, responseToCache, ttl)
		}
	}
}

// generateCacheKey генерирует ключ кэша
func generateCacheKey(path, query string) string {
	h := md5.New()
	h.Write([]byte(fmt.Sprintf("%s?%s", path, query)))
	return "http:" + hex.EncodeToString(h.Sum(nil))
}

// SafeCacheMiddleware создает middleware для кэширования GET запросов с проверкой готовности кэша
func SafeCacheMiddleware(ttl time.Duration) gin.HandlerFunc {
	return func(c *gin.Context) {
		// Проверяем что глобальный кэш готов
		if !IsGlobalCacheReady() {
			c.Next()
			return
		}

		cache := GetGlobalRedisCache()
		if cache == nil {
			c.Next()
			return
		}

		// Кэшируем только GET запросы
		if c.Request.Method != http.MethodGet {
			c.Next()
			return
		}

		// Генерируем ключ кэша на основе URL и query параметров
		key := generateCacheKey(c.Request.URL.Path, c.Request.URL.RawQuery)

		// Пытаемся получить из кэша
		var cachedResponse struct {
			Status  int               `json:"status"`
			Headers map[string]string `json:"headers"`
			Body    []byte            `json:"body"`
		}

		ctx := context.Background()
		err := cache.Get(ctx, key, &cachedResponse)
		if err == nil {
			// Восстанавливаем заголовки
			for k, v := range cachedResponse.Headers {
				c.Header(k, v)
			}
			// Отправляем кэшированный ответ
			c.Data(cachedResponse.Status, c.ContentType(), cachedResponse.Body)
			c.Abort()
			return
		}

		// Создаем custom writer для перехвата ответа
		w := &responseWriter{
			ResponseWriter: c.Writer,
			body:           bytes.NewBuffer(nil),
		}
		c.Writer = w

		// Обрабатываем запрос
		c.Next()

		// Кэшируем только успешные ответы
		if c.Writer.Status() >= 200 && c.Writer.Status() < 300 {
			responseToCache := struct {
				Status  int               `json:"status"`
				Headers map[string]string `json:"headers"`
				Body    []byte            `json:"body"`
			}{
				Status:  c.Writer.Status(),
				Headers: make(map[string]string),
				Body:    w.body.Bytes(),
			}

			// Сохраняем важные заголовки
			for k, v := range c.Writer.Header() {
				if len(v) > 0 {
					responseToCache.Headers[k] = v[0]
				}
			}

			// Сохраняем в кэш
			cache.Set(ctx, key, responseToCache, ttl)
		}
	}
}
