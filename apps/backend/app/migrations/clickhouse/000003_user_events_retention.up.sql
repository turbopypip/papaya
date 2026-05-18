ALTER TABLE papaya_analytics.user_events
MODIFY TTL
    toDateTime(created_at) + INTERVAL 60 DAY DELETE WHERE event_type = 'recommendation_impression',
    toDateTime(created_at) + INTERVAL 365 DAY DELETE WHERE event_type = 'recommendation_clicked',
    toDateTime(created_at) + INTERVAL 180 DAY DELETE WHERE event_type = 'thread_viewed',
    toDateTime(created_at) + INTERVAL 730 DAY DELETE WHERE event_type IN (
        'thread_created',
        'post_created',
        'comment_created',
        'post_liked',
        'comment_liked'
    ),
    toDateTime(created_at) + INTERVAL 365 DAY DELETE WHERE event_type NOT IN (
        'recommendation_impression',
        'recommendation_clicked',
        'thread_viewed',
        'thread_created',
        'post_created',
        'comment_created',
        'post_liked',
        'comment_liked'
    );
