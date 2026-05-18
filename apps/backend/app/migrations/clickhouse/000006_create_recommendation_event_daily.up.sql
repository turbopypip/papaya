CREATE TABLE IF NOT EXISTS papaya_analytics.recommendation_event_daily
(
    event_date Date,
    user_id UUID,
    thread_id UUID,
    model_version LowCardinality(String),
    impressions UInt64,
    clicks UInt64,
    position_sum UInt64,
    position_events UInt64
)
ENGINE = SummingMergeTree
PARTITION BY toYYYYMM(event_date)
ORDER BY (event_date, model_version, user_id, thread_id)
TTL event_date + INTERVAL 2 YEAR;
