from __future__ import annotations

from datetime import datetime, timezone
import math
import re

import polars as pl

from recommender.data import normalize_datetime_columns


def _title_tokens(value: str | None) -> set[str]:
    if not value:
        return set()
    return {token for token in re.findall(r"[a-zA-Zа-яА-Я0-9_]{3,}", value.lower())}


def popular_recent(interactions: pl.DataFrame, limit: int = 100, half_life_days: float = 14.0) -> list[tuple[str, float]]:
    if interactions.is_empty():
        return []
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    decay = math.log(2) / max(half_life_days, 1.0)
    interactions = normalize_datetime_columns(interactions, ["last_event_at"])
    ranked = (
        interactions.with_columns(
            ((pl.lit(now) - pl.col("last_event_at")).dt.total_days()).clip(0, None).alias("age_days")
        )
        .with_columns((pl.col("score") * (-decay * pl.col("age_days")).exp()).alias("recent_score"))
        .group_by("thread_id")
        .agg(pl.sum("recent_score").alias("score"))
        .sort("score", descending=True)
        .head(limit)
    )
    return list(zip(ranked.get_column("thread_id").to_list(), ranked.get_column("score").to_list(), strict=True))


def latest_active(threads: pl.DataFrame, interactions: pl.DataFrame, limit: int = 100) -> list[tuple[str, float]]:
    if threads.is_empty():
        return []
    threads = normalize_datetime_columns(threads, ["created_at", "updated_at"])
    interactions = normalize_datetime_columns(interactions, ["last_event_at"])
    activity = (
        interactions.group_by("thread_id")
        .agg(pl.max("last_event_at").alias("activity_at"), pl.sum("score").alias("activity_score"))
        if interactions.height
        else pl.DataFrame(schema={"thread_id": pl.Utf8, "activity_at": pl.Datetime, "activity_score": pl.Float64})
    )
    ranked = (
        threads.select("thread_id", "created_at")
        .join(activity, on="thread_id", how="left")
        .with_columns(
            pl.coalesce(["activity_at", "created_at"]).alias("rank_at"),
            pl.col("activity_score").fill_null(0.0),
        )
        .sort(["rank_at", "activity_score"], descending=[True, True])
        .head(limit)
    )
    scores = list(range(ranked.height, 0, -1))
    return list(zip(ranked.get_column("thread_id").to_list(), [float(score) for score in scores], strict=True))


def category_popular(user_id: str, business_threads: pl.DataFrame, interactions: pl.DataFrame, limit: int = 100) -> list[tuple[str, float]]:
    if business_threads.is_empty() or interactions.is_empty():
        return popular_recent(interactions, limit=limit)
    user_threads = interactions.filter(pl.col("user_id") == user_id).select("thread_id")
    if user_threads.is_empty():
        return popular_recent(interactions, limit=limit)

    categories = (
        user_threads.join(business_threads.select("thread_id", "categories"), on="thread_id", how="left")
        .explode("categories")
        .drop_nulls("categories")
        .get_column("categories")
        .unique()
        .to_list()
    )
    if not categories:
        return popular_recent(interactions, limit=limit)

    candidate_threads = business_threads.filter(
        pl.col("categories").list.eval(pl.element().is_in(categories)).list.any()
    ).select("thread_id")
    ranked = (
        interactions.join(candidate_threads, on="thread_id", how="inner")
        .group_by("thread_id")
        .agg(pl.sum("score").alias("score"))
        .sort("score", descending=True)
        .head(limit)
    )
    return list(zip(ranked.get_column("thread_id").to_list(), ranked.get_column("score").to_list(), strict=True))


def thread_affinity_recent(user_id: str, threads: pl.DataFrame, interactions: pl.DataFrame, limit: int = 100) -> list[tuple[str, float]]:
    if threads.is_empty():
        return []
    threads = normalize_datetime_columns(threads, ["created_at", "updated_at"])
    interactions = normalize_datetime_columns(interactions, ["last_event_at"])
    user_thread_ids = (
        set(interactions.filter(pl.col("user_id") == user_id).get_column("thread_id").to_list())
        if interactions.height
        else set()
    )
    if not user_thread_ids:
        return latest_active(threads, interactions, limit=limit)

    thread_rows = threads.select("thread_id", "title", "categories", "author_user_id", "created_at").iter_rows(named=True)
    history_categories: set[str] = set()
    history_authors: set[str] = set()
    history_tokens: set[str] = set()
    candidates: list[dict[str, object]] = []
    for row in thread_rows:
        categories = set(row["categories"] or [])
        tokens = _title_tokens(row["title"])
        if row["thread_id"] in user_thread_ids:
            history_categories.update(categories)
            if row["author_user_id"]:
                history_authors.add(row["author_user_id"])
            history_tokens.update(tokens)
        candidates.append({**row, "categories_set": categories, "title_tokens": tokens})

    if not history_categories and not history_authors and not history_tokens:
        return latest_active(threads, interactions, limit=limit)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    ranked: list[tuple[str, float]] = []
    for row in candidates:
        created_at = row["created_at"]
        age_days = max((now - created_at).days, 0) if created_at else 365
        freshness = math.exp(-math.log(2) * age_days / 30.0)
        category_score = float(len(row["categories_set"] & history_categories))
        author_score = 1.5 if row["author_user_id"] in history_authors else 0.0
        title_score = min(float(len(row["title_tokens"] & history_tokens)) * 0.25, 1.5)
        score = category_score + author_score + title_score + freshness
        if score > 0:
            ranked.append((str(row["thread_id"]), score))
    ranked.sort(key=lambda item: item[1], reverse=True)
    return ranked[:limit]
