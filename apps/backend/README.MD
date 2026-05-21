# Papaya Backend

Backend Papaya - Go API форума. Он отвечает за auth, RBAC, треды, посты, комментарии, лайки, вложения, realtime events, запись аналитики и проксирование персональных рекомендаций из FastAPI recommender service.

## Что внутри

- Go 1.24, Gin, GORM, PostgreSQL.
- JWT cookie sessions с настройками `AUTH_COOKIE_*`.
- Роли `user` и `admin`; dev-пользователь создается только в dev-режиме.
- Redis используется как backend cache.
- ClickHouse получает поведенческие события и агрегаты для recommender pipeline.
- Файлы сохраняются в `UPLOADS_PATH` и отдаются через `/uploads`.
- HTTP timeout в dev/prod конфиге - 30 секунд, чтобы первый recommendation request успевал прочитать артефакты и агрегаты.

## Запуск из корня

Обычный stack:

```bash
cp .env.example .env
docker compose up --build
```

Dev stack:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

Backend будет доступен на `http://localhost:8888`, healthcheck - `GET /api/v1/ping`.

## Локальная разработка

```bash
cd apps/backend/app
go mod download
LOCAL_CONFIG_PATH=config/local.yaml go run cmd/app/main.go
```

Для запуска без compose нужны доступные PostgreSQL, Redis и ClickHouse, а также переменные окружения из корневого `.env.example`: `POSTGRES_*`, `PG_PORT`, `SECRET`, `UPLOADS_PATH`, `CLICKHOUSE_*`, `RECOMMENDER_SERVICE_URL` и cookie-настройки.

## API surface

Базовый путь: `/api/v1`.

| группа | endpoints |
| --- | --- |
| health | `GET /ping` |
| auth | `POST /auth/signup`, `POST /auth/login`, `POST /auth/logout`, `GET /auth/validate`, `POST /auth/dev-login` в dev |
| threads | `POST /thread`, `GET /thread/all`, `GET /thread/search`, `GET /thread/:id`, `PUT /thread/:id`, `DELETE /thread/:id` |
| posts | `POST /post`, `GET /post`, `GET /post/search`, `PUT /post/:id`, `DELETE /post/:id` |
| comments | `POST /comment`, `GET /comment`, `PUT /comment/:id`, `DELETE /comment/:id` |
| likes | `POST /like`, `POST /like/batch`, `GET /like`, `DELETE /like` |
| attachments | `POST /attachment`, static `/uploads/*` |
| realtime | `GET /events/thread/:threadId` |
| analytics | `POST /analytics/thread/:id/view`, `POST /analytics/recommendations/event` |
| recommendations | `GET /recommendations/threads?limit=10` |
| roles/users | `POST /role`, `GET /user` |

Подробные контракты вложений, аналитики и рекомендаций описаны в `../../docs/api.md`.

## Данные

PostgreSQL хранит бизнес-сущности форума и metadata вложений. При старте backend выполняет GORM automigrate, создает `pg_trgm` extension, индексы для поиска тредов, unique index лайков и индекс владельца вложений.

ClickHouse не блокирует пользовательские сценарии: если запись аналитики временно недоступна, ошибка логируется, а forum operation завершается. Миграции ClickHouse применяются compose job `clickhouse-migrate`.

Рекомендации backend получает из FastAPI recommender service. Поле `score` уже нормализовано сервисом для сортировки по убыванию; backend не пересчитывает модельные score и только догружает thread/author details из PostgreSQL.

Backend пишет сильные пользовательские сигналы для recommender: `thread_viewed`, `post_liked`, `comment_liked`, `post_created`, `comment_created` и `recommendation_clicked`. `recommendation_impression` также сохраняется в ClickHouse, но используется для аналитики/CTR, а не как самостоятельный сигнал включения model-выдачи. Текущий frontend отправляет recommendation impressions/clicks только с главной страницы (`placement=home_recommendations`); страница треда рекомендационный блок не рендерит.

## Dev-пользователь

В dev-режиме создается пользователь:

- email: `dev@papaya.local`;
- пароль: `papaya-dev-password`;
- роль: `DEV_USER_ROLE=admin` по умолчанию, можно заменить на `user`.

## Проверки

```bash
cd apps/backend/app
go test ./...
```

## Docker

Dockerfile находится в `apps/backend/Dockerfile`. Основной запуск проекта находится в корневом `docker-compose.yml`; `apps/backend/docker-compose.yml` оставлен для совместимости со старым локальным запуском backend.
