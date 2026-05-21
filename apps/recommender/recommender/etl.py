from __future__ import annotations

from datetime import datetime, timezone
import logging
import math

import polars as pl

from recommender.config import DEFAULT_EVENT_WEIGHTS
from recommender.data import BehaviorData, BusinessData, PreparedData, normalize_datetime_columns

logger = logging.getLogger(__name__)

POSTGRES_DERIVED_EVENT_TYPES = {
    "post_created",
    "comment_created",
    "post_liked",
    "comment_liked",
    "thread_created",
}


def _debug_frame(name: str, frame: pl.DataFrame) -> None:
    logger.debug("%s rows=%s schema=%s sample=%s", name, frame.height, frame.schema, frame.head(3).to_dicts())


def _analytics_event_types(behavior: BehaviorData, raw_events: pl.DataFrame) -> set[str]:
    event_types: set[str] = set()
    if behavior.user_thread_daily.height:
        event_types.update(behavior.user_thread_daily.get_column("event_type").unique().to_list())
    if raw_events.height:
        event_types.update(raw_events.get_column("event_type").unique().to_list())
    return event_types


def _should_use_postgres_fallback(event_type: str, analytics_event_types: set[str]) -> bool:
    return event_type not in analytics_event_types


def build_interactions(
    business: BusinessData,
    behavior: BehaviorData,
    event_weights: dict[str, float] | None = None,
    half_life_days: float = 21.0,
    now: datetime | None = None,
) -> pl.DataFrame:
    weights = event_weights or DEFAULT_EVENT_WEIGHTS
    now = now or datetime.now(timezone.utc)
    now_naive = now.replace(tzinfo=None) if now.tzinfo else now
    users = normalize_datetime_columns(business.users, ["created_at"])
    threads = normalize_datetime_columns(business.threads, ["created_at", "updated_at"])
    posts = normalize_datetime_columns(business.posts, ["created_at", "updated_at"])
    comments = normalize_datetime_columns(business.comments, ["created_at", "updated_at"])
    likes = normalize_datetime_columns(business.likes, ["created_at"])
    raw_events = normalize_datetime_columns(behavior.events, ["created_at"])
    analytics_event_types = _analytics_event_types(behavior, raw_events)
    skipped_derived_event_types = sorted(POSTGRES_DERIVED_EVENT_TYPES & analytics_event_types)
    if skipped_derived_event_types:
        logger.info(
            "Skipping PostgreSQL-derived interaction events already available from ClickHouse: %s",
            ", ".join(skipped_derived_event_types),
        )

    frames: list[pl.DataFrame] = []
    if behavior.user_thread_daily.height:
        frames.append(
            behavior.user_thread_daily.select(
                pl.col("user_id"),
                pl.col("thread_id"),
                pl.col("event_type"),
                pl.col("event_date").cast(pl.Datetime(time_zone=None)).alias("created_at"),
                pl.col("events_count").cast(pl.Float64).alias("event_count"),
            )
        )
    elif raw_events.height:
        frames.append(
            raw_events.group_by(["user_id", "thread_id", "event_type"]).agg(
                pl.len().cast(pl.Float64).alias("event_count"),
                pl.max("created_at").cast(pl.Datetime(time_zone=None)).alias("created_at"),
            )
        )

    if posts.height and _should_use_postgres_fallback("post_created", analytics_event_types):
        frames.append(
            posts.select(
                pl.col("user_id"),
                pl.col("thread_id"),
                pl.lit("post_created").alias("event_type"),
                pl.col("created_at").cast(pl.Datetime(time_zone=None)),
                pl.lit(1.0).alias("event_count"),
            )
        )
    if comments.height and _should_use_postgres_fallback("comment_created", analytics_event_types):
        frames.append(
            comments.select(
                pl.col("user_id"),
                pl.col("thread_id"),
                pl.lit("comment_created").alias("event_type"),
                pl.col("created_at").cast(pl.Datetime(time_zone=None)),
                pl.lit(1.0).alias("event_count"),
            )
        )
    use_post_likes = _should_use_postgres_fallback("post_liked", analytics_event_types)
    use_comment_likes = _should_use_postgres_fallback("comment_liked", analytics_event_types)
    if likes.height and (use_post_likes or use_comment_likes):
        liked_events = likes.with_columns(
            pl.when(pl.col("likable_type") == "comment")
            .then(pl.lit("comment_liked"))
            .otherwise(pl.lit("post_liked"))
            .alias("event_type")
        )
        liked_events = liked_events.filter(
            ((pl.col("event_type") == "post_liked") & pl.lit(use_post_likes))
            | ((pl.col("event_type") == "comment_liked") & pl.lit(use_comment_likes))
        )
        frames.append(
            liked_events.select(
                pl.col("user_id"),
                pl.col("thread_id"),
                pl.col("event_type"),
                pl.col("created_at").cast(pl.Datetime(time_zone=None)),
                pl.lit(1.0).alias("event_count"),
            )
        )
    if threads.height and _should_use_postgres_fallback("thread_created", analytics_event_types):
        frames.append(
            threads.select(
                pl.col("author_user_id").alias("user_id"),
                pl.col("thread_id"),
                pl.lit("thread_created").alias("event_type"),
                pl.col("created_at").cast(pl.Datetime(time_zone=None)),
                pl.lit(1.0).alias("event_count"),
            )
        )

    if not frames:
        return pl.DataFrame(
            schema={
                "user_id": pl.Utf8,
                "thread_id": pl.Utf8,
                "score": pl.Float64,
                "last_event_at": pl.Datetime,
                "events_count": pl.Float64,
            }
        )

    interactions = pl.concat(frames, how="diagonal_relaxed").filter(
        pl.col("user_id").is_not_null() & pl.col("thread_id").is_not_null()
    )
    _debug_frame("interaction_events", interactions)
    weight_map = pl.DataFrame(
        {"event_type": list(weights.keys()), "event_weight": list(weights.values())},
        schema_overrides={"event_type": pl.Utf8, "event_weight": pl.Float64},
    )
    decay = math.log(2) / max(half_life_days, 1.0)
    result = (
        interactions.lazy()
        .join(weight_map.lazy(), on="event_type", how="left")
        .with_columns(pl.col("event_weight").fill_null(0.5))
        .with_columns(
            ((pl.lit(now_naive) - pl.col("created_at").cast(pl.Datetime(time_zone=None))).dt.total_days())
            .clip(0, None)
            .alias("age_days")
        )
        .with_columns((pl.col("event_count") * pl.col("event_weight") * (-decay * pl.col("age_days")).exp()).alias("score"))
        .group_by(["user_id", "thread_id"])
        .agg(
            pl.sum("score").alias("score"),
            pl.max("created_at").alias("last_event_at"),
            pl.sum("event_count").alias("events_count"),
            pl.when(pl.col("event_type") == "thread_viewed")
            .then(pl.col("event_count"))
            .otherwise(0.0)
            .sum()
            .alias("thread_viewed_count"),
            pl.when(pl.col("event_type").is_in(["post_liked", "comment_liked"]))
            .then(pl.col("event_count"))
            .otherwise(0.0)
            .sum()
            .alias("like_count"),
            pl.when(pl.col("event_type") == "recommendation_clicked")
            .then(pl.col("event_count"))
            .otherwise(0.0)
            .sum()
            .alias("recommendation_clicked_count"),
            pl.when(pl.col("event_type") == "post_created")
            .then(pl.col("event_count"))
            .otherwise(0.0)
            .sum()
            .alias("post_created_count"),
            pl.when(pl.col("event_type") == "comment_created")
            .then(pl.col("event_count"))
            .otherwise(0.0)
            .sum()
            .alias("comment_created_count"),
        )
        .filter(pl.col("score") > 0)
        .collect()
    )
    logger.info("Prepared interactions rows=%s users=%s threads=%s", result.height, users.height, threads.height)
    _debug_frame("interactions", result)
    return result


def split_train_test_by_time(interactions: pl.DataFrame, test_ratio: float = 0.2) -> tuple[pl.DataFrame, pl.DataFrame]:
    if interactions.is_empty() or interactions.height < 2:
        return interactions, interactions.clear()
    ordered = normalize_datetime_columns(interactions, ["last_event_at"]).sort("last_event_at")
    split_at = max(1, int(ordered.height * (1 - test_ratio)))
    return ordered.head(split_at), ordered.tail(ordered.height - split_at)


def prepare_data(
    business: BusinessData,
    behavior: BehaviorData,
    half_life_days: float,
    now: datetime | None = None,
) -> PreparedData:
    interactions = build_interactions(business, behavior, half_life_days=half_life_days, now=now)
    train, test = split_train_test_by_time(interactions)
    user_ids = sorted(interactions.get_column("user_id").unique().to_list()) if interactions.height else []
    thread_ids = sorted(interactions.get_column("thread_id").unique().to_list()) if interactions.height else []
    return PreparedData(
        interactions=interactions,
        train_interactions=train,
        test_interactions=test,
        user_ids=user_ids,
        thread_ids=thread_ids,
    )
