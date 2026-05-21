from __future__ import annotations

import logging

import polars as pl
from sqlalchemy import text

from recommender.data import (
    BehaviorData,
    BusinessData,
    EMPTY_COMMENTS,
    EMPTY_EVENTS,
    EMPTY_LIKES,
    EMPTY_POSTS,
    EMPTY_RECOMMENDATION_DAILY,
    EMPTY_THREADS,
    EMPTY_USER_THREAD_DAILY,
    EMPTY_USERS,
    empty_frame,
    normalize_datetime_columns,
)

logger = logging.getLogger(__name__)


def _query_postgres(engine, sql: str, schema: dict[str, pl.DataType]) -> pl.DataFrame:
    with engine.connect() as conn:
        rows = conn.execute(text(sql)).mappings().all()
    if not rows:
        return empty_frame(schema)
    return pl.DataFrame([dict(row) for row in rows], schema_overrides=schema)


def load_business_data(engine) -> BusinessData:
    users = _query_postgres(
        engine,
        """
        SELECT id::text AS user_id, username, created_at
        FROM users
        WHERE deleted_at IS NULL
        """,
        EMPTY_USERS,
    )
    threads = _query_postgres(
        engine,
        """
        SELECT
            t.id::text AS thread_id,
            t.title,
            t.categories,
            COALESCE(string_agg(p.content, E'\n' ORDER BY p.created_at), '') AS content,
            t.user_id::text AS author_user_id,
            t.created_at,
            t.updated_at
        FROM threads t
        LEFT JOIN posts p ON p.thread_id = t.id AND p.deleted_at IS NULL
        WHERE t.deleted_at IS NULL
        GROUP BY t.id, t.title, t.categories, t.user_id, t.created_at, t.updated_at
        """,
        EMPTY_THREADS,
    )
    posts = _query_postgres(
        engine,
        """
        SELECT id::text AS post_id, thread_id::text, user_id::text, content, created_at, updated_at
        FROM posts
        WHERE deleted_at IS NULL
        """,
        EMPTY_POSTS,
    )
    comments = _query_postgres(
        engine,
        """
        SELECT c.id::text AS comment_id, c.post_id::text, p.thread_id::text,
               c.user_id::text, c.content, c.created_at, c.updated_at
        FROM comments c
        JOIN posts p ON p.id = c.post_id
        WHERE c.deleted_at IS NULL AND p.deleted_at IS NULL
        """,
        EMPTY_COMMENTS,
    )
    likes = _query_postgres(
        engine,
        """
        SELECT l.id::text AS like_id, l.user_id::text, l.likable_id::text,
               l.likable_type, COALESCE(p.thread_id, cp.thread_id)::text AS thread_id,
               l.created_at
        FROM likes l
        LEFT JOIN posts p ON l.likable_type = 'post' AND p.id = l.likable_id
        LEFT JOIN comments c ON l.likable_type = 'comment' AND c.id = l.likable_id
        LEFT JOIN posts cp ON cp.id = c.post_id
        WHERE l.deleted_at IS NULL
        """,
        EMPTY_LIKES,
    )
    logger.info(
        "Loaded business data users=%s threads=%s posts=%s comments=%s likes=%s",
        users.height,
        threads.height,
        posts.height,
        comments.height,
        likes.height,
    )
    return BusinessData(
        users=normalize_datetime_columns(users, ["created_at"]),
        threads=normalize_datetime_columns(threads, ["created_at", "updated_at"]),
        posts=normalize_datetime_columns(posts, ["created_at", "updated_at"]),
        comments=normalize_datetime_columns(comments, ["created_at", "updated_at"]),
        likes=normalize_datetime_columns(likes, ["created_at"]),
    )


def _clickhouse_frame(client, sql: str, schema: dict[str, pl.DataType]) -> pl.DataFrame:
    result = client.query(sql)
    if not result.result_rows:
        return empty_frame(schema)
    rows = [dict(zip(result.column_names, row, strict=True)) for row in result.result_rows]
    return pl.DataFrame(rows, schema_overrides=schema)


def load_behavior_data(client, days: int = 180) -> BehaviorData:
    days = max(1, int(days))
    events = _clickhouse_frame(
        client,
        f"""
        SELECT
            toString(user_id) AS user_id,
            event_type,
            entity_type,
            toString(entity_id) AS entity_id,
            toString(thread_id) AS thread_id,
            metadata,
            created_at
        FROM user_events
        WHERE created_at >= now() - INTERVAL {int(days)} DAY
        """,
        EMPTY_EVENTS,
    )
    user_thread_daily = _clickhouse_frame(
        client,
        f"""
        SELECT
            event_date,
            toString(user_id) AS user_id,
            toString(thread_id) AS thread_id,
            event_type,
            sum(events_count) AS events_count
        FROM user_thread_event_daily
        WHERE event_date >= today() - INTERVAL {days} DAY
        GROUP BY event_date, user_id, thread_id, event_type
        """,
        EMPTY_USER_THREAD_DAILY,
    )
    recommendation_daily = _clickhouse_frame(
        client,
        f"""
        SELECT
            event_date,
            toString(user_id) AS user_id,
            toString(thread_id) AS thread_id,
            model_version,
            impressions,
            clicks,
            ctr,
            avg_position
        FROM recommendation_event_daily_stats
        WHERE event_date >= today() - INTERVAL {days} DAY
        """,
        EMPTY_RECOMMENDATION_DAILY,
    )
    logger.info(
        "Loaded behavior data raw_events=%s daily_events=%s recommendation_daily=%s",
        events.height,
        user_thread_daily.height,
        recommendation_daily.height,
    )
    logger.debug("Behavior events schema=%s sample=%s", events.schema, events.head(3).to_dicts())
    logger.debug("Behavior user_thread_daily schema=%s sample=%s", user_thread_daily.schema, user_thread_daily.head(3).to_dicts())
    logger.debug("Behavior recommendation_daily schema=%s sample=%s", recommendation_daily.schema, recommendation_daily.head(3).to_dicts())
    return BehaviorData(
        events=normalize_datetime_columns(events, ["created_at"]),
        user_thread_daily=user_thread_daily,
        recommendation_daily=recommendation_daily,
    )
