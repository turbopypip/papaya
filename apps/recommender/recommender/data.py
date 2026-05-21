from __future__ import annotations

from dataclasses import dataclass

import polars as pl


@dataclass
class BusinessData:
    users: pl.DataFrame
    threads: pl.DataFrame
    posts: pl.DataFrame
    comments: pl.DataFrame
    likes: pl.DataFrame


@dataclass
class BehaviorData:
    events: pl.DataFrame
    user_thread_daily: pl.DataFrame
    recommendation_daily: pl.DataFrame


@dataclass
class PreparedData:
    interactions: pl.DataFrame
    train_interactions: pl.DataFrame
    test_interactions: pl.DataFrame
    user_ids: list[str]
    thread_ids: list[str]


EMPTY_USERS = {"user_id": pl.Utf8, "username": pl.Utf8, "created_at": pl.Datetime}
EMPTY_THREADS = {
    "thread_id": pl.Utf8,
    "title": pl.Utf8,
    "categories": pl.List(pl.Utf8),
    "content": pl.Utf8,
    "author_user_id": pl.Utf8,
    "created_at": pl.Datetime,
    "updated_at": pl.Datetime,
}
EMPTY_POSTS = {
    "post_id": pl.Utf8,
    "thread_id": pl.Utf8,
    "user_id": pl.Utf8,
    "content": pl.Utf8,
    "created_at": pl.Datetime,
    "updated_at": pl.Datetime,
}
EMPTY_COMMENTS = {
    "comment_id": pl.Utf8,
    "post_id": pl.Utf8,
    "thread_id": pl.Utf8,
    "user_id": pl.Utf8,
    "content": pl.Utf8,
    "created_at": pl.Datetime,
    "updated_at": pl.Datetime,
}
EMPTY_LIKES = {
    "like_id": pl.Utf8,
    "user_id": pl.Utf8,
    "likable_id": pl.Utf8,
    "likable_type": pl.Utf8,
    "thread_id": pl.Utf8,
    "created_at": pl.Datetime,
}
EMPTY_EVENTS = {
    "user_id": pl.Utf8,
    "event_type": pl.Utf8,
    "entity_type": pl.Utf8,
    "entity_id": pl.Utf8,
    "thread_id": pl.Utf8,
    "metadata": pl.Utf8,
    "created_at": pl.Datetime,
}
EMPTY_USER_THREAD_DAILY = {
    "event_date": pl.Date,
    "user_id": pl.Utf8,
    "thread_id": pl.Utf8,
    "event_type": pl.Utf8,
    "events_count": pl.Float64,
}
EMPTY_RECOMMENDATION_DAILY = {
    "event_date": pl.Date,
    "user_id": pl.Utf8,
    "thread_id": pl.Utf8,
    "model_version": pl.Utf8,
    "impressions": pl.Float64,
    "clicks": pl.Float64,
    "ctr": pl.Float64,
    "avg_position": pl.Float64,
}


def empty_frame(schema: dict[str, pl.DataType]) -> pl.DataFrame:
    return pl.DataFrame(schema=schema)


def normalize_datetime_columns(frame: pl.DataFrame, columns: list[str]) -> pl.DataFrame:
    """Return datetime columns as timezone-naive UTC datetimes."""
    if frame.is_empty():
        return frame
    expressions = []
    for column in columns:
        dtype = frame.schema.get(column)
        if dtype is None:
            continue
        expression = pl.col(column)
        if getattr(dtype, "time_zone", None):
            expression = expression.dt.convert_time_zone("UTC").dt.replace_time_zone(None)
        else:
            expression = expression.cast(pl.Datetime(time_zone=None))
        expressions.append(expression.alias(column))
    return frame.with_columns(expressions) if expressions else frame
