CREATE TABLE IF NOT EXISTS papaya_analytics.user_thread_event_daily
(
    event_date Date,
    user_id UUID,
    thread_id UUID,
    event_type LowCardinality(String),
    events_count UInt64
)
ENGINE = SummingMergeTree
PARTITION BY toYYYYMM(event_date)
ORDER BY (event_date, user_id, thread_id, event_type)
TTL event_date + INTERVAL 2 YEAR;
