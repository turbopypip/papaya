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
- `NEXT_PUBLIC_API_URL` - публичный URL backend для frontend.

## Документация

- [API](docs/api.md)
- [Архитектура](docs/architecture.md)
- [Деплой](docs/deployment.md)
