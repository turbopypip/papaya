CREATE VIEW IF NOT EXISTS papaya_analytics.recommendation_event_daily_stats
AS
SELECT
    event_date,
    user_id,
    thread_id,
    model_version,
    impressions,
    clicks,
    if(impressions = 0, 0, clicks / impressions) AS ctr,
    if(position_events = 0, 0, position_sum / position_events) AS avg_position,
    position_events
FROM
(
    SELECT
        event_date,
        user_id,
        thread_id,
        model_version,
        sum(impressions) AS impressions,
        sum(clicks) AS clicks,
        sum(position_sum) AS position_sum,
        sum(position_events) AS position_events
    FROM papaya_analytics.recommendation_event_daily
    GROUP BY
        event_date,
        user_id,
        thread_id,
        model_version
);
