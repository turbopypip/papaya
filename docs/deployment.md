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

Raw analytics events are retained through ClickHouse TTL rules:

- `recommendation_impression`: 60 days;
- `recommendation_clicked`: 365 days;
- `thread_viewed`: 180 days;
- `thread_created`, `post_created`, `comment_created`, `post_liked`, `comment_liked`: 730 days;
- unknown event types: 365 days.

ClickHouse keeps model-ready daily aggregates for 2 years:

- `papaya_analytics.user_thread_event_daily`: `user_id x thread_id x event_type`;
- `papaya_analytics.recommendation_event_daily`: recommendation impressions, clicks, and position sums by `model_version`;
- `papaya_analytics.recommendation_event_daily_stats`: derived CTR and average position view.

Use aggregates as the primary training source. Use raw `user_events` for debugging and short-window analysis.

Run ClickHouse migrations manually with:

```bash
docker compose run --rm clickhouse-migrate
```

Useful verification queries are stored in `apps/backend/app/migrations/clickhouse/check_events.sql`.
