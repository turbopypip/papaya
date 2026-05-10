package main

// TODO: add everything logging
// TODO: update auth middleware to check user's role permissions
// TODO: add redis for caching popular queries

import (
	"log"
	"papaya-backend/internal/cache"
	"papaya-backend/internal/config"
	http_server "papaya-backend/internal/http-server"
	"papaya-backend/internal/logger"
	"papaya-backend/internal/storage"
)

func main() {
	// Инициализируем логгер
	logger.InitLogger()

	// Инициализируем хранилище
	storage.InitStorage()

	// Инициализируем Redis кэш
	cleanup, err := cache.InitRedis(config.MustLoad().Redis)
	if err != nil {
		log.Fatalf("Failed to initialize Redis cache: %v", err)
	}
	defer cleanup()

	log.Println("Redis cache initialized successfully")

	// Запускаем HTTP сервер
	http_server.RunServer()
}
