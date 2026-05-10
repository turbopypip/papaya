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

Frontend читает адрес backend из переменной `NEXT_PUBLIC_API_URL`.

Пример:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8888 npm run dev
```
