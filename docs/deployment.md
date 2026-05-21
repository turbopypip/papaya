# Развертывание

## Локальная Проверка

Для локальной Docker-проверки используйте:

```bash
docker compose up --build
```

Это обычный production-like путь. Он запускает backend, frontend, PostgreSQL, Redis, ClickHouse, миграции ClickHouse и `recommender-service` без загрузки fixtures Stack Exchange, синтетических данных или demo-тредов. Пустые бизнес-таблицы и пустые таблицы аналитики являются валидным начальным состоянием.

Для dev-стека используйте:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

Dev-стек сохраняет тот же путь рекомендаций без датасета и добавляет только frontend hot reload и dev-пользователя. Demo-данные подключаются отдельно через `docker-compose.recommender-demo.yml`.

## ClickHouse

Стек включает ClickHouse для аналитики рекомендаций. Имя базы аналитики зафиксировано миграциями как `papaya_analytics`, а job `clickhouse-migrate` применяет миграции из `apps/backend/app/migrations/clickhouse` через `golang-migrate`. Host, user и password настраиваются через переменные окружения.

Сырые события аналитики хранятся по TTL-правилам ClickHouse:

- `recommendation_impression`: 60 дней;
- `recommendation_clicked`: 365 дней;
- `thread_viewed`: 180 дней;
- `thread_created`, `post_created`, `comment_created`, `post_liked`, `comment_liked`: 730 дней;
- неизвестные типы событий: 365 дней.

ClickHouse хранит дневные агрегаты, готовые для модели, в течение 2 лет:

- `papaya_analytics.user_thread_event_daily`: `user_id x thread_id x event_type`;
- `papaya_analytics.recommendation_event_daily`: impressions, clicks и суммы позиций по `model_version`;
- `papaya_analytics.recommendation_event_daily_stats`: view с CTR и средней позицией.

Агрегаты используются как основной источник для обучения. Сырые `user_events` нужны для отладки и коротких аналитических окон.

Запустить миграции ClickHouse вручную:

```bash
docker compose run --rm clickhouse-migrate
```

Полезные проверочные SQL-запросы лежат в `apps/backend/app/migrations/clickhouse/check_events.sql`.

## Задачи Обучения Рекомендаций

Python recommender находится в `apps/recommender`.

Установка зависимостей для локального запуска:

```bash
cd apps/recommender
uv sync
```

Обучить модель:

```bash
cd apps/recommender
uv run python -m recommender.train_model --env-file ../../.env
```

Сгенерировать snapshots истории рекомендаций в ClickHouse:

```bash
cd apps/recommender
uv run python -m recommender.generate_recommendations --env-file ../../.env
```

Также доступны одноразовые Docker jobs:

```bash
docker compose run --rm recommender-train
docker compose run --rm recommender-generate
```

По умолчанию обучение использует `RECOMMENDER_MODEL_TYPE=catboost_ranker`: обычные jobs обучают и serving-ят одну production-модель CatBoostRanker без сравнения winner/champion. Artifact в `apps/recommender/artifacts/model.joblib` содержит CatBoost-модель и feature schema; `metadata.json` хранит версию модели, `feature_schema_version`, run id, параметры, `score_direction=negated_catboost_prediction` и ranking metrics. Online serving выполняет `recommender-service`: FastAPI service загружает CatBoostRanker artifact и `content_index.joblib`, логирует `model_loaded=true` и `model_version` при старте и проверяется Docker healthcheck.

Backend вызывает `RECOMMENDER_SERVICE_URL`, получает ранжированные thread ids и metadata аналитики, затем догружает детали тредов из PostgreSQL. Generation записывает recommendation snapshots в `papaya_analytics.recommendation_history`; cold-start и sparse-history fallbacks явно помечаются в `recommendation_source`, а UI-точка показа передается отдельно как `placement`. В текущем frontend рекомендации рендерятся только на главной странице с `placement=home_recommendations`; страницы тредов записывают просмотры, но не рендерят блок рекомендаций. Статусы запусков, content guardrails, sampled-ranking metrics, full-catalog sanity metrics, score-distribution статистика и `pairwise_auc` хранятся в `papaya_analytics.recommendation_runs`.

Для CPU-only Docker demo задавайте `OPENBLAS_NUM_THREADS=1`, чтобы recommender jobs предсказуемо работали на CPU. Единый человекочитаемый отчет для защиты создается отдельной командой `recommender.reporting --input docs/recommendation-big-test-report.json` и записывается в `recommendation-model-report.md` в корне репозитория.

Состояния пустой выдачи recommendation serving:

- artifact отсутствует: `model_not_ready`, это не ответ пустого каталога;
- PostgreSQL-каталог тредов пустой: `200` со статусом `no_recommendations` и пустым списком;
- новый пользователь при наличии реальных тредов: явный source `fallback_*`, пока поведения недостаточно для model scoring.

Порог активации по умолчанию: `RECOMMENDER_MIN_MODEL_INTERACTIONS=20`. Он считается по сильным пользовательским сигналам: `thread_viewed`, `post_liked`, `comment_liked`, `recommendation_clicked`, `post_created` и `comment_created`. Recommendation impressions сохраняются для аналитики и CTR, но сами по себе не включают model scoring. Serving также фильтрует собственные, просмотренные, лайкнутые и открытые из рекомендаций треды, поэтому demo-каталог должен содержать достаточно непотребленных тредов в предпочтительных категориях пользователя, чтобы персонализация была видна при ручном тестировании.

Content fixture можно пересобрать из Stack Exchange Data Dump `Posts.xml` и опционального `Comments.xml`; сохраняются тексты вопросов, тексты ответов, комментарии, source URLs, licenses и attribution:

```bash
cd apps/recommender
uv run recommender-import-stackexchange /path/to/Posts.xml \
  --comments-xml /path/to/Comments.xml \
  --limit 1000
```
