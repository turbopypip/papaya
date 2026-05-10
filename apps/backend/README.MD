# Papaya Backend

Backend-приложение Papaya написано на Go. Оно предоставляет API форума, работает с PostgreSQL и использует Redis для кэша.

## Запуск из корня проекта

Рекомендуемый способ локального запуска - через корневой Docker Compose:

```bash
cp .env.example .env
docker compose up --build
```

Backend будет доступен на `http://localhost:8888`.

## Локальная разработка

Из директории backend:

```bash
cd apps/backend/app
go mod download
LOCAL_CONFIG_PATH=config/local.yaml go run cmd/app/main.go
```

Для работы приложения также нужны переменные окружения из корневого `.env.example`: настройки PostgreSQL, Redis, `SECRET` и `UPLOADS_PATH`.

## Docker

Backend Dockerfile лежит в `apps/backend/Dockerfile`. Старый локальный compose в `apps/backend/docker-compose.yml` оставлен для совместимости, но основной запуск проекта находится в корневом `docker-compose.yml`.
