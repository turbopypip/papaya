# Architecture

Papaya is organized as a monorepo.

- `apps/backend` contains the Go API.
- `apps/frontend` contains the Next.js application.
- `infra/docker` is reserved for Docker and deployment-related files.
- Root `docker-compose.yml` starts the full local stack.

PostgreSQL stores forum business data: users, roles, threads, posts, comments, likes, and attachments. ClickHouse stores append-only behavioral events for recommendation model training. The backend writes analytics events through a dedicated service, and failed analytics writes are logged without failing the forum operation. For production load, the analytics service can be extended with a durable buffer or queue between forum handlers and ClickHouse.
