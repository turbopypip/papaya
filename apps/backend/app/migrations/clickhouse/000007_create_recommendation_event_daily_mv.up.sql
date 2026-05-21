CREATE MATERIALIZED VIEW IF NOT EXISTS papaya_analytics.recommendation_event_daily_mv
TO papaya_analytics.recommendation_event_daily
AS
SELECT
    toDate(created_at) AS event_date,
    user_id,
    thread_id,
    if(JSONExtractString(metadata, 'model_version') = '', 'unknown', JSONExtractString(metadata, 'model_version')) AS model_version,
    countIf(event_type = 'recommendation_impression') AS impressions,
    countIf(event_type = 'recommendation_clicked') AS clicks,
    sumIf(JSONExtractUInt(metadata, 'position'), event_type = 'recommendation_impression') AS position_sum,
    countIf(event_type = 'recommendation_impression' AND JSONHas(metadata, 'position')) AS position_events
FROM papaya_analytics.user_events
WHERE event_type IN ('recommendation_impression', 'recommendation_clicked')
GROUP BY
    event_date,
    user_id,
    thread_id,
    model_version;
