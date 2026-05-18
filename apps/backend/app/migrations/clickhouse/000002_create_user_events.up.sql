CREATE TABLE IF NOT EXISTS papaya_analytics.user_events
(
    user_id UUID,
    event_type LowCardinality(String),
    entity_type LowCardinality(String),
    entity_id UUID,
    thread_id UUID,
    metadata String DEFAULT '{}',
    created_at DateTime64(3, 'UTC') DEFAULT now64(3)
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(created_at)
ORDER BY (user_id, thread_id, created_at);
