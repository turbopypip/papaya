# Deployment

Deployment notes will live here.

For local Docker verification, start with:

```bash
docker compose up --build
```

For the development stack, use:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

The stack includes ClickHouse for recommendation analytics. The analytics database name is fixed by migrations as `papaya_analytics`, and the `clickhouse-migrate` job applies migrations from `apps/backend/app/migrations/clickhouse` with `golang-migrate`. Configure the host, user, and password through environment variables.

Run ClickHouse migrations manually with:

```bash
docker compose run --rm clickhouse-migrate
```

Useful verification queries are stored in `apps/backend/app/migrations/clickhouse/check_events.sql`.
