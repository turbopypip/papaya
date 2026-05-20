# Papaya Recommender

Python pipeline for Papaya thread recommendations.

## Goal

The recommender target architecture is one trainable model:

```text
User encoder + Thread encoder -> score(user, thread)
```

The model must treat both sides as real forum entities.

- User encoder: history, categories of interest, views, likes, comments, created posts, recommendation clicks, recency, and interaction strength.
- Thread encoder: `title`, `categories`, `content`, author, freshness, popularity, early activity, real post text, and real comment text when available.
- Output: a single score for a user/thread pair.

Normal serving should use only the selected trained model. Cold-start/fallback is a separate protective path for new or sparse-history users.

## Storage Boundaries

- PostgreSQL stores forum business entities only.
- ClickHouse stores behavioral events, aggregates, recommendation history, run status, and metrics.
- FastAPI recommender service loads the winner artifact and generates online recommendations on request.
- Backend calls the service for ranked thread ids and loads thread details from PostgreSQL.

## Local Setup

```bash
uv sync
```

Run from `apps/recommender` and pass the root env file explicitly:

```bash
uv run python -m recommender.train_model --env-file ../../.env
uv run python -m recommender.generate_recommendations --env-file ../../.env
uv run python -m recommender.api --env-file ../../.env --host 0.0.0.0 --port 8000
```

## Docker Jobs

```bash
docker compose run --rm recommender-train
docker compose run --rm recommender-generate
```

Training writes `apps/recommender/artifacts/model.joblib` and `metadata.json`. The FastAPI service loads that artifact for request-time serving. Generation loads the same artifact and stores recommendation snapshots in ClickHouse.

## Model Selection

Task 9.2 compares four ways to train the same `score(user, thread)` objective:

1. Entity-feature classifier on sklearn.
2. Learning-to-rank model.
3. Factorization Machine / LightFM-style model with user and thread features.
4. Two-tower neural model.

All candidates must use the same train/test split, positive examples, negative sampling strategy, user/thread features, users, candidate threads, seed, and top-K metrics.

The winner is selected by ranking quality and guardrails:

```text
champion_score =
  0.45 * NDCG@K
+ 0.25 * Recall@K
+ 0.15 * MAP@K
+ 0.10 * coverage
+ 0.05 * diversity
```

After winner selection, the normal train/generate path should use only the winner model. Alternative candidates are evaluation-only.

## Cold Start

`RECOMMENDER_MIN_MODEL_INTERACTIONS` controls when model scores are trusted.

For new or sparse-history users, fallback recommendations may use freshness, popularity, categories, and content. These results must be explicitly marked as `fallback_*`. They are not the main model path.

## Real-Content Big Test

Task 9.4 should validate the model on real text, not just synthetic titles.

The big-test dataset should use real technical content, preferably from Stack Exchange Data Dump:

- question/thread title;
- tags/categories;
- question body as thread content;
- answer bodies as post text;
- comment text when available;
- source URL, license, and attribution.

The dataset is then converted into Papaya structures:

- `BusinessData.users`;
- `BusinessData.threads`;
- `BusinessData.posts`;
- `BusinessData.comments`;
- `BusinessData.likes`;
- `BehaviorData.events`;
- `BehaviorData.user_thread_daily`;
- `BehaviorData.recommendation_daily`.

The test should create user behavior over that real content, compare the four 9.2 training variants, select the winner, run the final winner-only pipeline, and verify:

- `model_trained=true`;
- normal recommendations have source `model`;
- fallback appears only for new or sparse-history users;
- train/test split has no future user-thread leakage;
- different users receive different ranked lists;
- `recommendation_history` and `recommendation_runs` are populated.

Run the current report generator:

```bash
uv run python -m recommender.synthetic \
  --seed 9400 \
  --include-evaluation \
  --output ../../docs/recommendation-big-test-report.json

uv run python -m recommender.reporting \
  --output ../../recommendation-model-report.md
```

## Stack Exchange Fixture

The local fixture lives at:

```text
apps/recommender/fixtures/stackexchange_titles.jsonl
```

Rebuild it from Stack Exchange dump files:

```bash
uv run recommender-import-stackexchange /path/to/Posts.xml \
  --comments-xml /path/to/Comments.xml \
  --limit 1000
```

Fixture rows should preserve `source_url`, `license`, and `attribution`.

## Loader

Load a generated fixture into real test stores:

```bash
uv run python -m recommender.synthetic_loader \
  --env-file ../../.env \
  --dataset-id recommendation-big-test \
  --run-id recommendation-big-test-run \
  --validate
```

## Serving Contract

`POST /recommendations/threads` accepts `user_id` and `limit`, then returns ranked items with:

- `thread_id`;
- `score`;
- `recommendation_source` as `model` or `fallback_*`;
- `model_version`;
- `run_id` and request-level `generation_id`;
- metadata for analytics.

UI location is not part of `recommendation_source`; frontend analytics sends it separately as `placement`.
