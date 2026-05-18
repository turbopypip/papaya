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

Redis stores the current online recommendation output. Recommendations are written as Sorted Sets keyed by user, where scores represent the latest model ranking. Redis may also keep lightweight metadata required for fast serving, but durable history and model metrics belong in ClickHouse.

The Python recommender reads forum entities from PostgreSQL and behavioral features from ClickHouse. After each run it writes the current online recommendations to Redis, and writes recommendation history, `recommendation_runs`, and run metrics to ClickHouse.

The backend recommendations endpoint reads ranked thread ids from Redis, then loads thread details and author data from PostgreSQL before returning the response to the frontend.
