CREATE MATERIALIZED VIEW IF NOT EXISTS papaya_analytics.user_thread_event_daily_mv
TO papaya_analytics.user_thread_event_daily
AS
SELECT
    toDate(created_at) AS event_date,
    user_id,
    thread_id,
    event_type,
    count() AS events_count
FROM papaya_analytics.user_events
GROUP BY
    event_date,
    user_id,
    thread_id,
    event_type;
