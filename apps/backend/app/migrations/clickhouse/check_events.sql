-- Event counts by type.
SELECT event_type, count() AS events_count
FROM papaya_analytics.user_events
GROUP BY event_type
ORDER BY events_count DESC;

-- Events for a concrete user. Replace the UUID before running.
SELECT *
FROM papaya_analytics.user_events
WHERE user_id = toUUID('00000000-0000-0000-0000-000000000000')
ORDER BY created_at DESC
LIMIT 100;

-- User x thread interaction matrix for recommendation training.
SELECT user_id, thread_id, event_type, count() AS events_count
FROM papaya_analytics.user_events
GROUP BY user_id, thread_id, event_type
ORDER BY user_id, thread_id, event_type;

-- Daily aggregated user x thread x event matrix for model training.
SELECT
    event_date,
    user_id,
    thread_id,
    event_type,
    sum(events_count) AS events_count
FROM papaya_analytics.user_thread_event_daily
GROUP BY
    event_date,
    user_id,
    thread_id,
    event_type
ORDER BY event_date DESC, events_count DESC
LIMIT 100;

-- Daily recommendation metrics with derived CTR and average position.
SELECT
    event_date,
    model_version,
    total_impressions,
    total_clicks,
    if(total_impressions = 0, 0, total_clicks / total_impressions) AS ctr,
    if(total_position_events = 0, 0, total_position_sum / total_position_events) AS avg_position
FROM
(
    SELECT
        event_date,
        model_version,
        sum(impressions) AS total_impressions,
        sum(clicks) AS total_clicks,
        sum(position_sum) AS total_position_sum,
        sum(position_events) AS total_position_events
    FROM papaya_analytics.recommendation_event_daily
    GROUP BY
        event_date,
        model_version
)
ORDER BY event_date DESC, total_impressions DESC
LIMIT 100;

-- Current table definition, including raw-event TTL.
SHOW CREATE TABLE papaya_analytics.user_events;

-- Latest events in the log.
SELECT *
FROM papaya_analytics.user_events
WHERE created_at >= now() - INTERVAL 1 DAY
ORDER BY created_at DESC
LIMIT 100;
