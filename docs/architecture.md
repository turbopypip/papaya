# Architecture

Papaya is organized as a monorepo.

- `apps/backend` contains the Go API.
- `apps/frontend` contains the Next.js application.
- `infra/docker` is reserved for Docker and deployment-related files.
- Root `docker-compose.yml` starts the full local stack.

## Recommendation Data Flow

The recommendation system separates operational forum data from behavioral analytics and online serving data.

PostgreSQL stores only forum business data: users, roles, threads, posts, comments, likes, and attachments. It is the source of truth for thread details, authors, permissions, and other data needed to render the forum, but it does not store recommendation history, model runs, or serving state.

ClickHouse stores append-only behavioral events, daily aggregates, recommendation serving history, `recommendation_runs`, and model metrics. The backend writes analytics events through a dedicated service, and failed analytics writes are logged without failing the forum operation. Raw ClickHouse events have TTL-based retention: impressions are kept for 60 days, recommendation clicks for 365 days, thread views for 180 days, strong forum events for 730 days, and unknown event types for 365 days. Daily aggregate tables keep `user_id x thread_id x event_type` and recommendation metrics for 2 years; these aggregates are the primary source for model training, while raw events are for debugging and short-window analysis. For production load, the analytics service can be extended with a durable buffer or queue between forum handlers and ClickHouse.

Redis is used by the backend for forum caching, not as the target recommendation serving store. Recommendation serving happens through the FastAPI recommender service, while durable history and model metrics belong in ClickHouse.

The Python recommender reads forum entities from PostgreSQL and behavioral features from ClickHouse. Training writes the selected winner artifact. The FastAPI service loads that artifact and generates ranked thread ids on request. Offline generation writes recommendation history, `recommendation_runs`, and run metrics to ClickHouse.

The backend recommendations endpoint calls the FastAPI recommender service for ranked thread ids, scores, `recommendation_source`, `model_version`, `run_id`/`generation_id`, then loads thread details and author data from PostgreSQL before returning the response to the frontend.

## Recommender Module

`apps/recommender` is a Python module with a two-step pipeline:

- `train_model.py` loads users, threads, posts, comments, likes, ClickHouse events, and daily aggregates; builds a decayed implicit-feedback matrix; selects a winner across the four 9.2 candidates when no winner artifact exists, otherwise retrains only the saved winner model type; and saves the champion artifact plus a human-readable report.
- `generate_recommendations.py` loads the champion artifact, builds top-N thread recommendations from that one ML model, excludes already-seen and own threads, applies explicitly marked fallback baselines only for cold-start/sparse-history users or empty model output, and persists recommendation history in ClickHouse.
- `api.py` exposes FastAPI request-time serving. It loads the winner artifact, regenerates current behavior context from PostgreSQL and ClickHouse, and returns `thread_id`, `score`, `recommendation_source`, `model_version`, `run_id`/`generation_id`, and metadata for analytics.

The 9.2 selection candidates are `entity_feature_sgd`, `learning_to_rank_sgd`, `factorization_machine_svd`, and `two_tower_dot`. `RECOMMENDER_MODEL_TYPE=winner` is the default: it uses the saved winner after selection, while `auto`/`compare` is reserved for explicit offline comparison. Baselines are kept for comparison and fallback only: `popular_recent`, `category_popular`, and `latest_active`. Offline reports include Recall@K, NDCG@K, MAP@K, HitRate@K, coverage, diversity, novelty, personalization, champion score, model selection guardrails, and content-aware guardrails.

The content-aware retrieval layer builds embeddings from `title + categories + content`. It uses `sentence-transformers` and FAISS when those optional packages are installed, and falls back to sklearn hashing plus numpy search for CPU-only Docker demos. Embeddings are cached by `content_hash` and reused from disk, so heavy embedding/index work stays in offline recommender jobs and out of the backend request path.
