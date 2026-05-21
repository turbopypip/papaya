# Papaya Frontend

Frontend Papaya - Next.js 14 приложение форума. Оно работает с Go API через Axios, хранит серверное состояние в TanStack Query и показывает персональные рекомендации, полученные backend-ом из FastAPI recommender service.

## Что реализовано

- login, signup, logout и dev-login в dev-режиме;
- домашняя страница со списком тредов, поиском, созданием тредов и блоком рекомендаций;
- страница треда с постами, комментариями, лайками, вложениями, редактированием и поиском по постам;
- загрузка и отображение вложений для тредов, постов и комментариев;
- analytics events для просмотров тредов, recommendation impressions и recommendation clicks;
- Next.js rewrites для `/api/v1/*` и `/uploads/*`.

Frontend не пересчитывает рекомендации и не меняет модельный score: он показывает порядок, который вернул backend/recommender service, а UI-точку показа отправляет в analytics как отдельный `placement`.

Текущее UI-состояние рекомендаций: блок рекомендаций есть только на домашней странице (`placement=home_recommendations`). Страница треда не показывает похожие/дополнительные рекомендации, но по-прежнему пишет `thread_viewed` при открытии треда. Клик по карточке рекомендации пишет `recommendation_clicked`, после чего тред считается потребленным кандидатом и больше не должен возвращаться в рекомендациях для этого пользователя.

## Стек

- Next.js 14, React 18, TypeScript.
- Chakra UI, CSS modules.
- TanStack Query, Zustand.
- Axios, React Hook Form, Zod.
- Lucide React и React Icons.

## Запуск из корня

Рекомендуемый запуск всего проекта:

```bash
cp .env.example .env
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

Frontend будет доступен на `http://localhost:3000`.

## Локальная разработка

```bash
cd apps/frontend
npm install
npm run dev
```

Если backend запущен отдельно на `localhost:8888`, можно явно указать публичный API URL:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8888 npm run dev
```

Если `NEXT_PUBLIC_API_URL` пустой, frontend использует относительные `/api/v1` и `/uploads`, а Next.js rewrites проксируют их на `SERVER_API_URL`.

## Scripts

```bash
npm run dev
npm run build
npm run start
npm run lint
```

## Настройка API

`src/shared/consts.ts` строит base URL из `NEXT_PUBLIC_API_URL`.

- В dev compose `NEXT_PUBLIC_API_URL` пустой, `SERVER_API_URL=http://backend:8888`, поэтому браузер ходит через Next.js proxy.
- В обычном production compose `NEXT_PUBLIC_API_URL` по умолчанию становится `http://localhost:8888`, поэтому браузер ходит в backend напрямую.
- `/uploads/:path*` также проксируется через Next.js rewrites, если используется относительный URL.

## Основные директории

```text
src/app/                 # Next.js pages and providers
src/entities/            # thread, post, comment, user, like, attachment, recommendation
src/shared/              # axios clients, env helpers, common UI, globals
```

## Проверки

```bash
cd apps/frontend
npm run build
npm run lint
```
