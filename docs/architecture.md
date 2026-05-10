# Architecture

Papaya is organized as a monorepo.

- `apps/backend` contains the Go API.
- `apps/frontend` contains the Next.js application.
- `infra/docker` is reserved for Docker and deployment-related files.
- Root `docker-compose.yml` starts the full local stack.
