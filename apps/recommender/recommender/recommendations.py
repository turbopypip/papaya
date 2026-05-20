from __future__ import annotations

import polars as pl

from recommender.baselines import category_popular, latest_active, popular_recent, thread_affinity_recent
from recommender.content import ContentIndex, content_recommendations_for_user
from recommender.matrix import InteractionMatrix
from recommender.modeling import ModelResult, recommend_for_user


def excluded_threads_for_user(user_id: str, interactions: pl.DataFrame, threads: pl.DataFrame) -> set[str]:
    viewed = (
        set(interactions.filter(pl.col("user_id") == user_id).get_column("thread_id").to_list())
        if interactions.height
        else set()
    )
    own_threads = (
        set(threads.filter(pl.col("author_user_id") == user_id).get_column("thread_id").to_list())
        if threads.height
        else set()
    )
    return viewed | own_threads


def _merge_ranked_sources(sources: list[tuple[str, list[tuple[str, float]]]], exclude: set[str], limit: int) -> list[tuple[str, float, str]]:
    merged: dict[str, tuple[float, str]] = {}
    source_weight = {
        "model": 1.0,
        "content": 0.92,
        "thread_affinity_recent": 0.9,
        "category_popular": 0.85,
        "popular_recent": 0.7,
        "latest_active": 0.55,
    }
    for source, items in sources:
        for rank, (thread_id, score) in enumerate(items, start=1):
            if thread_id in exclude:
                continue
            normalized = float(score) * source_weight.get(source, 0.5) + 1.0 / rank
            previous = merged.get(thread_id)
            if previous is None or normalized > previous[0]:
                merged[thread_id] = (normalized, source)
    return [
        (thread_id, score, source)
        for thread_id, (score, source) in sorted(merged.items(), key=lambda item: item[1][0], reverse=True)[:limit]
    ]


def _fallback_source(source: str) -> str:
    return f"fallback_{source}"


def generate_for_users(
    user_ids: list[str],
    threads: pl.DataFrame,
    interactions: pl.DataFrame,
    matrix: InteractionMatrix,
    model_result: ModelResult,
    top_n: int,
    candidate_pool_size: int,
    min_model_interactions: int = 1,
    content_index: ContentIndex | None = None,
) -> dict[str, list[tuple[str, float, str]]]:
    popular = popular_recent(interactions, limit=candidate_pool_size)
    latest = latest_active(threads, interactions, limit=candidate_pool_size)
    output: dict[str, list[tuple[str, float, str]]] = {}
    for user_id in user_ids:
        exclude = excluded_threads_for_user(user_id, interactions, threads)
        user_events_count = (
            float(interactions.filter(pl.col("user_id") == user_id).get_column("events_count").sum())
            if interactions.height and user_id in set(interactions.get_column("user_id").to_list())
            else 0.0
        )
        use_model = user_events_count >= float(min_model_interactions)
        model_items = recommend_for_user(model_result, matrix, user_id, candidate_pool_size, exclude) if use_model else []
        if use_model and model_items:
            output[user_id] = [
                (thread_id, score, "model")
                for thread_id, score in model_items[:top_n]
            ]
            continue

        category_items = category_popular(user_id, threads, interactions, limit=candidate_pool_size)
        affinity_items = thread_affinity_recent(user_id, threads, interactions, limit=candidate_pool_size)
        content_items = (
            content_recommendations_for_user(user_id, interactions, content_index, candidate_pool_size, exclude)
            if content_index is not None
            else []
        )
        fallback_items = _merge_ranked_sources(
            [
                ("content", content_items),
                ("thread_affinity_recent", affinity_items),
                ("category_popular", category_items),
                ("popular_recent", popular),
                ("latest_active", latest),
            ],
            exclude,
            top_n,
        )
        output[user_id] = [(thread_id, score, _fallback_source(source)) for thread_id, score, source in fallback_items]
    return output
