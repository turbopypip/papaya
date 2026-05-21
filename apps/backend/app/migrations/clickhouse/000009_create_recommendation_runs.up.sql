CREATE TABLE IF NOT EXISTS papaya_analytics.recommendation_runs
(
    id UUID,
    model_version LowCardinality(String),
    started_at DateTime64(3, 'UTC'),
    finished_at Nullable(DateTime64(3, 'UTC')),
    users_count UInt64,
    recommendations_count UInt64,
    metrics String DEFAULT '{}',
    status LowCardinality(String),
    error String DEFAULT '',
    created_at DateTime64(3, 'UTC') DEFAULT now64(3)
)
ENGINE = ReplacingMergeTree(created_at)
PARTITION BY toYYYYMM(created_at)
ORDER BY id
TTL toDateTime(created_at) + INTERVAL 2 YEAR;
