CREATE TABLE IF NOT EXISTS papaya_analytics.recommendation_history
(
    id UUID,
    user_id UUID,
    thread_id UUID,
    score Float64,
    model_version LowCardinality(String),
    run_id UUID,
    generated_at DateTime64(3, 'UTC'),
    rank UInt32,
    source LowCardinality(String)
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(generated_at)
ORDER BY (user_id, generated_at, rank, thread_id)
TTL toDateTime(generated_at) + INTERVAL 2 YEAR;
