# Papaya Recommender

Python recommender отвечает за обучение, offline snapshots, big-test отчеты, загрузку demo-данных и online serving персональных рекомендаций для Papaya.

Финальное состояние: backend не хранит online-выдачу в Redis и не считает рекомендации сам. Он вызывает FastAPI service, а recommender service загружает CatBoostRanker artifact и генерирует ranked thread ids на request path.

## Storage boundaries

- PostgreSQL - бизнес-данные форума: users, roles, threads, posts, comments, likes, attachments.
- ClickHouse - поведенческие события, daily aggregates, recommendation history, `recommendation_runs`, метрики.
- `apps/recommender/artifacts` - `model.joblib`, `metadata.json`, `content_index.joblib`.
- Backend - API и догрузка thread/author details из PostgreSQL.
- Frontend - отображение рекомендаций на главной странице и отправка impressions/clicks с отдельным `placement`.

## Setup

```bash
uv sync
```

Локальные Python-команды ниже выполняются из `apps/recommender`.

## Local pipeline

```bash
uv run python -m recommender.train_model --env-file ../../.env
uv run python -m recommender.generate_recommendations --env-file ../../.env
uv run python -m recommender.api --env-file ../../.env --host 0.0.0.0 --port 8000
```

CLI entrypoints из `pyproject.toml`:

```bash
uv run recommender-train --env-file ../../.env
uv run recommender-generate --env-file ../../.env
uv run recommender-serve --env-file ../../.env --host 0.0.0.0 --port 8000
uv run recommender-report --input ../../docs/recommendation-big-test-report.json --output ../../recommendation-model-report.md
```

## Docker

Docker-команды выполняются из корня репозитория.

Основной service без датасета:

```bash
docker compose up --build recommender-service
```

Обычный `docker compose up --build` и dev stack запускают этот же online service. Они не вызывают `synthetic_loader`, Stack Exchange import, train или generate jobs. Для старта достаточно готовых файлов `apps/recommender/artifacts/model.joblib`, `metadata.json` и `content_index.joblib`; healthcheck проверяет, что модель загружена.

One-off jobs доступны через profile `jobs`:

```bash
docker compose --profile jobs run --rm recommender-train
docker compose --profile jobs run --rm recommender-generate
```

Demo stack с seed, train, generate и report:

```bash
docker compose -f docker-compose.yml -f docker-compose.recommender-demo.yml up --build
```

Demo tools:

```bash
docker compose -f docker-compose.yml -f docker-compose.recommender-demo.yml --profile demo-tools run --rm recommender-demo-refresh
docker compose -f docker-compose.yml -f docker-compose.recommender-demo.yml --profile demo-tools run --rm recommender-demo-clean
docker compose -f docker-compose.yml -f docker-compose.recommender-demo.yml run --rm recommender-demo-report
```

## Model pipeline

Training читает PostgreSQL и ClickHouse, строит decayed interactions и обучает единственную production-модель `CatBoostRanker`, которая считает `score(user, thread)` по feature matrix. CatBoost `YetiRank` prediction инвертируется в публичный score как `-catboost_prediction`, поэтому большее значение всегда означает более высокий ранг; это записывается в metadata как `score_direction=negated_catboost_prediction`.

Feature contract:

- user features: категории и токены из истории, просмотры, лайки, комментарии, созданные посты, recommendation clicks, recency и activity strength;
- thread features: категории, автор, свежесть, популярность, активность, длина title/content и агрегаты постов/комментариев/лайков;
- pair features: пересечение категорий, token similarity, seen/clicked/liked/commented flags, author affinity и recency-adjusted affinity.

Artifact format:

- `model.joblib` содержит `model_type=catboost_ranker`, CatBoost model, `feature_schema`, categorical feature names, hyperparameters и content flag;
- `metadata.json` содержит `feature_schema_version`, ranking metrics, run id, model version и параметры training flow;
- serving artifact не содержит обязательных `user_to_index`, `thread_to_index` и sparse matrix.

CatBoostRanker aggregate score для отчета:

```text
0.45 * NDCG@K
+ 0.25 * Recall@K
+ 0.15 * MAP@K
+ 0.10 * coverage
+ 0.05 * diversity
```

Сохраненный demo artifact сейчас использует:

| поле | значение |
| --- | --- |
| `model_version` | `demo-synthetic-v1` |
| production model | `catboost_ranker` |
| ranking score | см. `catboost_ranker_score` в `metadata.json` |
| normal source | `model` |
| content embedding backend | `sklearn_hashing` |
| content search backend | `numpy` |

Метрики большого отчета:

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

Sampled-ranking метрики валидируют модель на held-out positive threads против sampled negative candidates. Full-catalog metrics дополнительно показывают exact top-10 качество при ранжировании всего текущего каталога.

## Content layer

Content-aware layer строит embeddings из `title + categories + content`.

- Если установлены optional dependencies `sentence-transformers` и `faiss-cpu`, используется semantic embedding + FAISS.
- В CPU-only Docker demo используется fallback `sklearn_hashing` + numpy search.
- Индекс и content hash кэшируются в `content_index.joblib`.

## Serving contract

FastAPI:

- `GET /health`;
- `POST /recommendations/threads`.

Request:

```json
{
  "user_id": "uuid",
  "limit": 10,
  "events_days": 180
}
```

Response item:

```json
{
  "thread_id": "uuid",
  "score": 0.87,
  "recommendation_source": "model",
  "model_version": "demo-synthetic-v1",
  "run_id": "uuid",
  "generation_id": "uuid",
  "metadata": {
    "model_type": "catboost_ranker",
    "feature_schema_version": "catboost_ranker_features_v1"
  }
}
```

`recommendation_source=model` означает нормальную модельную выдачу. Cold-start и sparse-history fallback явно помечаются как `fallback_*`. UI placement не смешивается с source: frontend отправляет `placement` отдельным analytics field. В текущем frontend рекомендации показываются только на главной странице, поэтому штатный UI placement для recommendation events - `home_recommendations`.

Model-путь включается, когда пользователь накопил минимум `RECOMMENDER_MIN_MODEL_INTERACTIONS` сильных сигналов. Значение по умолчанию - `20`. В этот счет входят `thread_viewed`, `post_liked`, `comment_liked`, `recommendation_clicked`, `post_created` и `comment_created`; `recommendation_impression` остается аналитическим событием и не переводит пользователя из fallback в model само по себе.

Serving не рекомендует собственные или уже потребленные треды. Потребленными считаются треды, где у пользователя есть просмотр, лайк поста/комментария или клик по рекомендации. Если пользователь уже пролайкал или открыл все треды своей любимой категории, модель сохранит профиль интереса, но будет ранжировать оставшиеся кандидаты из других категорий, пока в каталоге не появятся новые подходящие треды.

Empty-state contract:

- artifact отсутствует: `status=model_not_ready`;
- PostgreSQL не содержит тредов: `status=no_recommendations`, `recommendations=[]`;
- новый пользователь при существующих тредах: `fallback_*` выдача, пока истории меньше `RECOMMENDER_MIN_MODEL_INTERACTIONS`.

## Offline generation

`recommender.generate_recommendations` загружает CatBoostRanker artifact, строит top-N рекомендации по текущему PostgreSQL catalog, исключает собственные и уже потребленные треды, затем пишет:

- `papaya_analytics.recommendation_history`;
- `papaya_analytics.recommendation_runs`.

Эти snapshots нужны для аудита, отчетов и demo-проверок. Online serving все равно генерируется FastAPI service на request path.

## Big synthetic test

Генератор `recommender.synthetic` проверяет модель на правдоподобной имитации форума с реальным техническим текстом из Stack Exchange/Stack Overflow fixture и synthetic top-up.

Текущий большой demo-scale:

- 50 пользователей;
- 1000 технических тредов;
- 27314 постов;
- 81460 комментариев;
- 1500 лайков;
- 159074 поведенческих событий;
- профили пользователей: `backend-heavy`, `frontend-heavy`, `devops-heavy`, `mixed-fullstack`, `noisy/low-signal`;
- topics: backend, frontend, devops, mixed, noise.

Сгенерировать JSON-отчет:

```bash
uv run python -m recommender.synthetic \
  --seed 9400 \
  --include-evaluation \
  --output ../../docs/recommendation-big-test-report.json
```

Собрать Markdown-отчет:

```bash
uv run python -m recommender.reporting \
  --input ../../docs/recommendation-big-test-report.json \
  --output ../../recommendation-model-report.md
```

Загрузить dataset в PostgreSQL и ClickHouse:

```bash
uv run python -m recommender.synthetic_loader \
  --env-file ../../.env \
  --dataset-id synthetic-big-test \
  --run-id synthetic-loader-run \
  --validate
```

Очистить dataset:

```bash
uv run python -m recommender.synthetic_loader \
  --env-file ../../.env \
  --dataset-id synthetic-big-test \
  --run-id synthetic-loader-run \
  --clear-only
```

## Stack Exchange fixture

Fixture хранится в:

```text
apps/recommender/fixtures/stackexchange_titles.jsonl
```

Он сохраняет `source_url`, `license`, `attribution`, question bodies, answer bodies и comments where available. Пересборка из Stack Exchange Data Dump:

```bash
uv run recommender-import-stackexchange /path/to/Posts.xml \
  --comments-xml /path/to/Comments.xml \
  --limit 1000
```

## Tests

```bash
uv run pytest
```

Точечные проверки:

```bash
uv run pytest tests/test_synthetic.py
uv run pytest tests/test_big_pipeline_evaluation.py
uv run pytest tests/test_pipeline_scripts.py
```
