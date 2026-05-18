# Architecture

Papaya is organized as a monorepo.

- `apps/backend` contains the Go API.
- `apps/frontend` contains the Next.js application.
- `infra/docker` is reserved for Docker and deployment-related files.
- Root `docker-compose.yml` starts the full local stack.

PostgreSQL stores forum business data: users, roles, threads, posts, comments, likes, and attachments. ClickHouse stores append-only behavioral events for recommendation model training. The backend writes analytics events through a dedicated service, and failed analytics writes are logged without failing the forum operation. Raw ClickHouse events have TTL-based retention: impressions are kept for 60 days, recommendation clicks for 365 days, thread views for 180 days, strong forum events for 730 days, and unknown event types for 365 days. Daily aggregate tables keep `user_id x thread_id x event_type` and recommendation metrics for 2 years; these aggregates are the primary source for model training, while raw events are for debugging and short-window analysis. For production load, the analytics service can be extended with a durable buffer or queue between forum handlers and ClickHouse.
