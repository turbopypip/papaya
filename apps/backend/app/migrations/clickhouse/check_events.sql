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

-- Latest events in the log.
SELECT *
FROM papaya_analytics.user_events
WHERE created_at >= now() - INTERVAL 1 DAY
ORDER BY created_at DESC
LIMIT 100;
