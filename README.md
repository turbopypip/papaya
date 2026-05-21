# Papaya

Papaya - fullstack-форум с Go backend, Next.js frontend и Python-сервисом персональных рекомендаций.

Проект уже собран вокруг финального продуктового пути: пользователь работает с форумом на `http://localhost:3000`, frontend обращается к Go API, backend хранит бизнес-данные в PostgreSQL, пишет поведенческую аналитику в ClickHouse и запрашивает персональные рекомендации у FastAPI recommender service.

## Структура

```text
papaya/
├── apps/
│   ├── backend/      # Go API, RBAC, PostgreSQL, Redis, ClickHouse analytics
│   ├── frontend/     # Next.js 14 приложение форума
│   └── recommender/  # Python training, demo data, reports, FastAPI serving
├── docs/
│   ├── api.md
│   ├── architecture.md
│   └── deployment.md
├── docker-compose.yml
├── docker-compose.dev.yml
├── docker-compose.recommender-demo.yml
├── .env.example
└── README.md
```

## Сервисы

| сервис | роль | порт |
| --- | --- | --- |
| `frontend` | Next.js UI | `3000` |
| `backend` | Go API `/api/v1` и `/uploads` | `8888` |
| `recommender-service` | FastAPI online recommendations | `8000` |
| `db` | PostgreSQL business storage | `5432` |
| `redis` | backend cache | `6379` |
| `clickhouse` | analytics, aggregates, recommendation history | `8123`, `9000` |
| `clickhouse-migrate` | one-off ClickHouse migrations | - |

## Быстрый запуск

Создайте локальный `.env`:

```bash
cp .env.example .env
```

Обычный Docker-запуск:

```bash
docker compose up --build
```

Обычный запуск поднимает PostgreSQL, ClickHouse, Redis, backend, frontend и `recommender-service` без demo/import датасета. PostgreSQL и ClickHouse могут быть пустыми: применяются только миграции и базовые роли, а FastAPI recommender использует готовые artifacts из `apps/recommender/artifacts`.

Dev-запуск с hot reload frontend и dev-пользователем:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

Полный demo-сценарий рекомендаций с большим синтетическим датасетом, обучением, генерацией истории и отчетом:

```bash
docker compose -f docker-compose.yml -f docker-compose.recommender-demo.yml up --build
```

После старта:

- frontend: `http://localhost:3000`;
- backend healthcheck: `http://localhost:8888/api/v1/ping`;
- recommender healthcheck: `http://localhost:8000/health`.

## Переменные окружения

Шаблон лежит в `.env.example`, реальный `.env` не коммитится.

Основные группы:

- `POSTGRES_*`, `PG_PORT` - подключение backend и recommender к PostgreSQL;
- `REDIS_*` - Redis cache для backend;
- `CLICKHOUSE_*` - ClickHouse analytics и HTTP-клиент recommender;
- `LOCAL_CONFIG_PATH`, `APP_ENV`, `ENV`, `LOG_LEVEL` - режим и YAML-конфиг backend;
- `SECRET`, `AUTH_COOKIE_*` - JWT cookie и настройки сессии;
- `UPLOADS_PATH` - директория файловых вложений backend;
- `DEV_USER_ROLE` - роль dev-пользователя в dev-режиме: `admin` или `user`;
- `RECOMMENDER_*` - версия CatBoostRanker-модели, директория артефактов, top-N, content layer и timeout генерации;
- `RECOMMENDER_SERVICE_URL` - URL FastAPI recommender service для backend. В Docker это `http://recommender-service:8000`; для локального backend без compose используйте `http://localhost:8000`;
- `SERVER_API_URL` - backend URL для Next.js rewrites внутри Docker-сети;
- `NEXT_PUBLIC_API_URL` - browser-facing backend URL. В dev compose он пустой, и frontend ходит через rewrites `/api/v1`; в production compose по умолчанию используется `http://localhost:8888`.

## Backend

Backend находится в `apps/backend/app` и написан на Go 1.24.

Он предоставляет:

- auth endpoints: signup, login, logout, validate, dev-login в dev-режиме;
- RBAC роли `user` и `admin`;
- CRUD для тредов, постов и комментариев;
- лайки, поиск тредов и постов;
- файловые вложения для тредов, постов и комментариев;
- SSE endpoint для событий треда;
- analytics endpoints для просмотров тредов и событий рекомендаций;
- recommendations endpoint, который обращается в FastAPI recommender service.

PostgreSQL хранит пользователей, роли, треды, посты, комментарии, лайки и metadata вложений. Redis используется для backend-кэша. ClickHouse получает append-only события и агрегаты для обучения рекомендаций. Файлы сохраняются в `apps/backend/uploads` и отдаются через `/uploads`.

Локальный запуск backend без compose:

```bash
cd apps/backend/app
go mod download
LOCAL_CONFIG_PATH=config/local.yaml go run cmd/app/main.go
```

Для такого запуска нужны доступные PostgreSQL, Redis и ClickHouse, а также переменные из корневого `.env`.

Проверки:

```bash
cd apps/backend/app
go test ./...
```

## Frontend

Frontend находится в `apps/frontend` и использует Next.js 14, React 18, TypeScript, Chakra UI, TanStack Query, Zustand и Axios.

Реализованы:

- login/signup и dev-login в dev-режиме;
- домашняя страница со списком тредов, поиском, созданием тредов и блоком рекомендаций;
- страница треда с постами, комментариями, лайками, вложениями и поиском по постам; рекомендации тредов на странице треда не показываются;
- отправка analytics events: `thread_viewed`, `recommendation_impression`, `recommendation_clicked`;
- проксирование `/api/v1/*` и `/uploads/*` через Next.js rewrites при пустом `NEXT_PUBLIC_API_URL`.

Локальный запуск frontend без compose:

```bash
cd apps/frontend
npm install
npm run dev
```

Если frontend запускается вне Docker, укажите публичный backend URL:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8888 npm run dev
```

Проверки:

```bash
cd apps/frontend
npm run build
npm run lint
```

## ClickHouse и аналитика

Docker Compose поднимает `clickhouse` и одноразовый job `clickhouse-migrate`, который применяет миграции из `apps/backend/app/migrations/clickhouse`.

База аналитики фиксирована миграциями как `papaya_analytics`.

Сырые события в `papaya_analytics.user_events` хранятся с TTL:

- `recommendation_impression` - 60 дней;
- `recommendation_clicked` - 365 дней;
- `thread_viewed` - 180 дней;
- `thread_created`, `post_created`, `comment_created`, `post_liked`, `comment_liked` - 730 дней;
- неизвестные типы событий - 365 дней.

Дневные агрегаты хранятся 2 года:

- `user_thread_event_daily` - матрица `user_id x thread_id x event_type`;
- `recommendation_event_daily` - impressions, clicks и суммы позиций по `model_version`;
- `recommendation_event_daily_stats` - view с CTR и средней позицией.

Запустить миграции вручную:

```bash
docker compose run --rm clickhouse-migrate
```

Проверочные SQL-запросы лежат в `apps/backend/app/migrations/clickhouse/check_events.sql`.

## Рекомендации

Recommender находится в `apps/recommender` и состоит из training pipeline, offline generation, demo loader/reporting и FastAPI serving.

Normal dev/prod serving не запускает обучение, comparison или demo import. `recommender-service` при старте загружает `model.joblib`, `metadata.json` и `content_index.joblib` из artifacts, логирует `model_loaded=true` и `model_version`, а Docker healthcheck требует загруженную модель. Если artifact отсутствует, это отдельное состояние `model_not_ready`, не пустая выдача.

Финальный flow:

1. Backend пишет форумные события и recommendation feedback в ClickHouse.
2. `recommender.train_model` читает PostgreSQL business data и ClickHouse behavior data.
3. `CatBoostRanker` обучается на ranking groups по пользователям и сохраняет production artifact с feature schema.
4. Normal train/generate/serve path всегда использует `model_type=catboost_ranker`; matrix/SVD и исторические offline candidates не участвуют в live serving.
5. `recommender.generate_recommendations` пишет snapshots в ClickHouse `recommendation_history` и статусы/метрики в `recommendation_runs`.
6. `recommender.api` обслуживает online request path: backend передает user id и limit, получает `thread_id`, `score`, `recommendation_source`, `model_version`, `run_id`, `generation_id`, а детали тредов догружает из PostgreSQL.

CatBoost `YetiRank` prediction нормализуется в публичный score как `-catboost_prediction`, поэтому большие значения `score` всегда означают более высокий ранг. Это зафиксировано в metadata как `score_direction=negated_catboost_prediction`.

Локальные команды:

```bash
cd apps/recommender
uv sync
uv run python -m recommender.train_model --env-file ../../.env
uv run python -m recommender.generate_recommendations --env-file ../../.env
uv run python -m recommender.api --env-file ../../.env --host 0.0.0.0 --port 8000
```

Docker one-off jobs:

```bash
docker compose --profile jobs run --rm recommender-train
docker compose --profile jobs run --rm recommender-generate
```

Текущий сохраненный demo artifact:

| поле | значение |
| --- | --- |
| `model_version` | `demo-synthetic-v1` |
| production model | `catboost_ranker` |
| normal source | `model` |
| content backend | `sklearn_hashing` |
| content search | `numpy` |
| artifacts | `apps/recommender/artifacts/model.joblib`, `metadata.json`, `content_index.joblib` |

Текущие метрики большого отчета CatBoostRanker:

| метрика | значение |
| --- | ---: |
| `CatBoostRanker score` | 0.5261 |
| sampled `Precision@10` | 0.7860 |
| sampled `Recall@10` | 0.0532 |
| sampled `NDCG@10` | 0.7937 |
| sampled `MAP@10` | 0.6863 |
| sampled `Hit rate@10` | 1.0000 |
| `pairwise_auc` | 0.7232 |
| full-catalog `Precision@10` | 0.3980 |
| full-catalog `NDCG@10` | 0.4031 |
| full-catalog `Hit rate@10` | 1.0000 |

Sampled-ranking метрики считаются на held-out positive threads против sampled negative candidates. Full-catalog block дополнительно проверяет exact top-10 попадания при ранжировании всего текущего каталога.

Fallback используется только для новых или sparse-history пользователей и всегда помечается как `fallback_*`. По умолчанию model-путь включается после `RECOMMENDER_MIN_MODEL_INTERACTIONS=20` сильных сигналов пользователя: просмотров тредов, лайков постов/комментариев, кликов по рекомендациям, созданных постов и комментариев. `recommendation_impression` пишется для аналитики, но не считается сильным сигналом для перехода из fallback в model.

Из кандидатов исключаются собственные треды пользователя, уже просмотренные треды, треды с лайками пользователя и треды, открытые кликом из рекомендаций. Поэтому если пользователь пролайкал все треды интересующей категории, модель будет выбирать из оставшихся кандидатов, даже если профиль интереса уже распознан. UI-точка показа передается отдельно как `placement`; текущий frontend показывает рекомендации только на главной странице с `placement=home_recommendations`.

Пустой каталог возвращает `200` со статусом `no_recommendations` и пустым списком. Cold-start/fallback включается только после появления реальных тредов в PostgreSQL.

## Demo-данные рекомендаций

Большой demo-набор создается из Stack Exchange/Stack Overflow fixture и synthetic top-up:

- 50 пользователей;
- 1000 технических тредов;
- 27314 постов;
- 81460 комментариев;
- 1500 лайков;
- 159074 поведенческих событий;
- профили интересов: backend, frontend, devops, mixed, noisy.

Demo-пользователи:

| профиль | email | пароль |
| --- | --- | --- |
| backend | `backend-user@papaya.demo` | `PapayaDemo1!` |
| frontend | `frontend-user@papaya.demo` | `PapayaDemo1!` |
| devops | `devops-user@papaya.demo` | `PapayaDemo1!` |
| mixed | `mixed-user@papaya.demo` | `PapayaDemo1!` |
| dev admin | `dev@papaya.local` | `papaya-dev-password` |

После ручных просмотров, лайков, комментариев и кликов по рекомендациям можно пересчитать выдачу:

```bash
docker compose -f docker-compose.yml -f docker-compose.recommender-demo.yml --profile demo-tools run --rm recommender-demo-refresh
```

Пересобрать Markdown-отчет:

```bash
docker compose -f docker-compose.yml -f docker-compose.recommender-demo.yml run --rm recommender-demo-report
```

Очистить demo-данные, recommendation history и runs:

```bash
docker compose -f docker-compose.yml -f docker-compose.recommender-demo.yml --profile demo-tools run --rm recommender-demo-clean
```

## Большой тест и отчеты

Сгенерировать machine-readable JSON:

```bash
cd apps/recommender
uv run python -m recommender.synthetic \
  --seed 9400 \
  --include-evaluation \
  --output ../../docs/recommendation-big-test-report.json
```

Собрать человекочитаемый отчет:

```bash
cd apps/recommender
uv run python -m recommender.reporting \
  --input ../../docs/recommendation-big-test-report.json \
  --output ../../recommendation-model-report.md
```

Загрузить synthetic fixture в реальные PostgreSQL и ClickHouse:

```bash
cd apps/recommender
uv run python -m recommender.synthetic_loader \
  --env-file ../../.env \
  --dataset-id synthetic-big-test \
  --run-id synthetic-loader-run \
  --validate
```

Пересобрать Stack Exchange fixture из Data Dump:

```bash
cd apps/recommender
uv run recommender-import-stackexchange /path/to/Posts.xml \
  --comments-xml /path/to/Comments.xml \
  --limit 1000
```

## Документация

- [API](docs/api.md)
- [Архитектура](docs/architecture.md)
- [Деплой](docs/deployment.md)
- [Backend README](apps/backend/README.MD)
- [Frontend README](apps/frontend/README.md)
- [Recommender README](apps/recommender/README.md)
