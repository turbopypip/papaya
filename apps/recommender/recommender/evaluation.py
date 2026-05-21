from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import polars as pl

from recommender.baselines import category_popular, latest_active, popular_recent
from recommender.catboost_ranker import (
    MODEL_TYPE,
    evaluate_catboost_ranker,
    generate_catboost_for_users,
    train_catboost_ranker,
)
from recommender.content import build_or_load_content_index, performance_guardrails
from recommender.etl import prepare_data
from recommender.metrics import ranking_report
from recommender.recommendations import excluded_threads_for_user
from recommender.serving import relevant_threads_by_user, thread_categories
from recommender.synthetic import SyntheticForumDataset


RECOMMENDER_ROOT = Path(__file__).resolve().parents[1]


def popularity_by_thread(interactions: pl.DataFrame) -> dict[str, float]:
    if interactions.is_empty():
        return {}
    return dict(
        interactions.group_by("thread_id")
        .agg(pl.sum("score").alias("score"))
        .iter_rows()
    )


def evaluate_recommendation_sets(
    recommendation_sets: dict[str, dict[str, list[str]]],
    test_interactions: pl.DataFrame,
    all_thread_ids: set[str],
    categories: dict[str, set[str]],
    popularity: dict[str, float],
    k: int = 10,
) -> dict[str, dict[str, float]]:
    relevant = relevant_threads_by_user(test_interactions)
    return {
        name: ranking_report(recommendations, relevant, all_thread_ids, categories, popularity, k=k)
        for name, recommendations in recommendation_sets.items()
    }


def baseline_recommendation_sets(
    user_ids: list[str],
    threads: pl.DataFrame,
    train_interactions: pl.DataFrame,
    top_n: int = 10,
) -> dict[str, dict[str, list[str]]]:
    popular = popular_recent(train_interactions, limit=max(top_n * 5, top_n))
    latest = latest_active(threads, train_interactions, limit=max(top_n * 5, top_n))
    outputs = {
        "popular_recent": {},
        "category_popular": {},
        "latest_active": {},
    }
    for user_id in user_ids:
        exclude = excluded_threads_for_user(user_id, train_interactions, threads)
        outputs["popular_recent"][user_id] = _without_excluded(popular, exclude, top_n)
        outputs["category_popular"][user_id] = _without_excluded(
            category_popular(user_id, threads, train_interactions, limit=max(top_n * 5, top_n)),
            exclude,
            top_n,
        )
        outputs["latest_active"][user_id] = _without_excluded(latest, exclude, top_n)
    return outputs


def big_test_user_examples(
    recommendations: dict[str, list[tuple[str, float, str]]],
    user_profiles: pl.DataFrame,
    thread_profiles: pl.DataFrame,
    limit_users: int = 5,
) -> list[dict[str, Any]]:
    profile_by_user = dict(user_profiles.select("user_id", "profile").iter_rows())
    topic_by_thread = dict(thread_profiles.select("thread_id", "topic").iter_rows())
    examples = []
    for user_id in sorted(recommendations)[:limit_users]:
        examples.append(
            {
                "user_id": user_id,
                "profile": profile_by_user.get(user_id, "unknown"),
                "recommendations": [
                    {
                        "rank": rank,
                        "thread_id": thread_id,
                        "topic": topic_by_thread.get(thread_id, "unknown"),
                        "score": score,
                        "source": source,
                    }
                    for rank, (thread_id, score, source) in enumerate(recommendations[user_id], start=1)
                ],
            }
        )
    return examples


def build_big_test_evaluation_report(
    dataset: SyntheticForumDataset,
    model_version: str = "catboost-ranker-v1",
    top_n: int = 10,
    candidate_pool_size: int = 50,
    half_life_days: float = 21.0,
    min_model_interactions: int = 20,
    random_state: int = 42,
    now: datetime | None = None,
) -> dict[str, Any]:
    prepared = prepare_data(dataset.business, dataset.behavior, half_life_days=half_life_days, now=now)
    model = train_catboost_ranker(
        dataset.business,
        prepared.train_interactions,
        random_state=random_state,
        top_n=top_n,
    )
    content_index = build_or_load_content_index(
        dataset.business.threads,
        artifacts_dir=RECOMMENDER_ROOT / "artifacts",
    )
    user_ids = dataset.business.users.get_column("user_id").to_list()
    generated = generate_catboost_for_users(
        user_ids,
        dataset.business,
        prepared.train_interactions,
        model,
        top_n=top_n,
        candidate_pool_size=candidate_pool_size,
        min_model_interactions=min_model_interactions,
    )
    metrics = evaluate_catboost_ranker(
        model,
        dataset.business,
        prepared.train_interactions,
        prepared.test_interactions,
        top_n=top_n,
        candidate_pool_size=candidate_pool_size,
        min_model_interactions=min_model_interactions,
        k=top_n,
    )
    return {
        "model_version": model_version,
        "model_type": MODEL_TYPE,
        "model_trained": model.trained,
        "feature_schema_version": model.feature_schema.version,
        "final_pipeline_model_type": MODEL_TYPE,
        "final_pipeline_uses_winner": False,
        "model_selection_enabled": False,
        "normal_sources": sorted({source for items in generated.values() for _thread_id, _score, source in items}),
        "hyperparameters": model.hyperparameters,
        "top_n": top_n,
        "metrics": metrics,
        "content_guardrails": performance_guardrails(content_index, 0.0),
        "users": _evaluation_user_rows(generated, dataset, prepared.train_interactions, top_n=top_n),
    }


def _without_excluded(items: list[tuple[str, float]], exclude: set[str], limit: int) -> list[str]:
    output = []
    for thread_id, _score in items:
        if thread_id in exclude:
            continue
        output.append(thread_id)
        if len(output) >= limit:
            break
    return output


def _evaluation_user_rows(
    generated: dict[str, list[tuple[str, float, str]]],
    dataset: SyntheticForumDataset,
    train_interactions: pl.DataFrame,
    top_n: int,
) -> list[dict[str, Any]]:
    profile_by_user = dict(dataset.user_profiles.select("user_id", "profile").iter_rows())
    topic_by_thread = dict(dataset.thread_profiles.select("thread_id", "topic").iter_rows())
    rows = []
    for user_id in sorted(generated):
        train_rows = (
            train_interactions.filter(pl.col("user_id") == user_id)
            .sort("score", descending=True)
            .head(10)
            .select("thread_id", "score", "events_count")
            .to_dicts()
            if train_interactions.height
            else []
        )
        excluded = sorted(excluded_threads_for_user(user_id, train_interactions, dataset.business.threads))
        rows.append(
            {
                "username": _username_for_user(dataset.business.users, user_id),
                "user_id": user_id,
                "profile": profile_by_user.get(user_id, "unknown"),
                "training_events": [
                    {
                        "thread_id": row["thread_id"],
                        "topic": topic_by_thread.get(row["thread_id"], "unknown"),
                        "score": row["score"],
                        "events_count": row["events_count"],
                    }
                    for row in train_rows
                ],
                "recommendations": [
                    {
                        "rank": rank,
                        "thread_id": thread_id,
                        "topic": topic_by_thread.get(thread_id, "unknown"),
                        "score": score,
                        "source": source,
                    }
                    for rank, (thread_id, score, source) in enumerate(generated[user_id][:top_n], start=1)
                ],
                "excluded_threads": [
                    {"thread_id": thread_id, "reason": "already viewed or authored in train"}
                    for thread_id in excluded[:25]
                ],
            }
        )
    return rows


def _username_for_user(users: pl.DataFrame, user_id: str) -> str:
    matched = users.filter(pl.col("user_id") == user_id)
    return matched.item(0, "username") if matched.height else user_id
