# Papaya

Papaya - fullstack-проект форума с backend на Go и frontend на Next.js.

## Структура

```text
papaya/
├── apps/
│   ├── backend/
│   └── frontend/
├── infra/
│   └── docker/
├── docs/
├── docker-compose.yml
├── docker-compose.dev.yml
├── .env.example
└── README.md
```

## Приложения

- `apps/backend` - Go API.
- `apps/frontend` - Next.js приложение.

## Локальный запуск

Создайте локальный файл окружения:

```bash
cp .env.example .env
```

Запустите весь проект:

```bash
docker compose up --build
```

Запуск с dev-настройками:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

## Переменные окружения

Шаблон переменных лежит в `.env.example`. Реальный `.env` не коммитится.

Основные группы переменных:

- `POSTGRES_*` - подключение к PostgreSQL.
- `REDIS_*` - подключение к Redis.
- `LOCAL_CONFIG_PATH` - путь к YAML-конфигу backend внутри контейнера.
- `SECRET` - секрет для JWT.
- `UPLOADS_PATH` - путь для файловых вложений.
- `DEV_USER_ROLE` - роль dev-пользователя в dev-режиме: `admin` по умолчанию или `user`.
- `AUTH_COOKIE_*` - настройки JWT cookie: domain, secure и sameSite.
- `SERVER_API_URL` - внутренний URL backend для Next.js proxy внутри Docker-сети.
- `NEXT_PUBLIC_API_URL` - публичный URL backend для frontend; по умолчанию пустой, чтобы браузер ходил через Next.js proxy `/api/v1`.

## Документация

- [API](docs/api.md)
- [Архитектура](docs/architecture.md)
- [Деплой](docs/deployment.md)
