# Papaya Frontend

Frontend-приложение Papaya написано на Next.js.

## Запуск из корня проекта

Рекомендуемый способ локального запуска всего проекта:

```bash
cp .env.example .env
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

Frontend будет доступен на `http://localhost:3000`.

## Локальная разработка

Из директории frontend:

```bash
cd apps/frontend
npm install
npm run dev
```

## Сборка

```bash
npm run build
```

## Настройка API

В Docker frontend по умолчанию использует относительный `/api/v1`, а Next.js проксирует запросы на `SERVER_API_URL=http://backend:8888` внутри Docker-сети.

Для локального запуска frontend без compose можно указать публичный backend URL:

Пример:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8888 npm run dev
```
