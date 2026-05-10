# Papaya

Papaya is a fullstack forum project with a Go backend and a Next.js frontend.

## Structure

```text
papaya/
├── apps/
│   ├── backend/
│   └── frontend/
├── infra/
│   └── docker/
├── docs/
├── docker-compose.yml
├── docker-compose.dev.yml
├── .env.example
└── README.md
```

## Apps

- `apps/backend` - Go API.
- `apps/frontend` - Next.js frontend.

## Local Setup

Create a local environment file:

```bash
cp .env.example .env
```

Start the full stack:

```bash
docker compose up --build
```

For development overrides:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

## Documentation

- [API](docs/api.md)
- [Architecture](docs/architecture.md)
- [Deployment](docs/deployment.md)
