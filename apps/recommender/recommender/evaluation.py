from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import polars as pl

from recommender.baselines import category_popular, latest_active, popular_recent
from recommender.content import build_or_load_content_index, content_recommendations_for_user, performance_guardrails
from recommender.etl import prepare_data
from recommender.matrix import build_interaction_matrix
from recommender.metrics import ranking_report
from recommender.recommendations import generate_for_users
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
    model_version: str = "entity-feature-v1",
    top_n: int = 10,
    candidate_pool_size: int = 50,
    half_life_days: float = 21.0,
    min_model_interactions: int = 20,
    random_state: int = 42,
    now: datetime | None = None,
) -> dict[str, Any]:
    from recommender.champion import evaluate_and_select_champion, selection_to_metrics

    prepared = prepare_data(dataset.business, dataset.behavior, half_life_days=half_life_days, now=now)
    matrix = build_interaction_matrix(prepared.train_interactions)
    selection = evaluate_and_select_champion(
        matrix,
        dataset.business.users,
        dataset.business.threads,
        prepared.train_interactions,
        prepared.test_interactions,
        prepared.interactions,
        top_n=top_n,
        candidate_pool_size=candidate_pool_size,
        random_state=random_state,
        k=top_n,
        candidate_model_types=("entity_feature", "learning_to_rank", "factorization_machine", "two_tower"),
    )
    model = selection.model_result
    content_index = build_or_load_content_index(
        dataset.business.threads,
        artifacts_dir=RECOMMENDER_ROOT / "artifacts",
    )
    user_ids = dataset.business.users.get_column("user_id").to_list()
    generated = generate_for_users(
        user_ids,
        dataset.business.threads,
        prepared.train_interactions,
        matrix,
        model,
        top_n=top_n,
        candidate_pool_size=candidate_pool_size,
        min_model_interactions=min_model_interactions,
        content_index=content_index,
    )
    model_recommendations = {
        user_id: [thread_id for thread_id, _score, _source in items]
        for user_id, items in generated.items()
    }
    baselines = baseline_recommendation_sets(user_ids, dataset.business.threads, prepared.train_interactions, top_n=top_n)
    content_only = {
        user_id: [
            thread_id
            for thread_id, _score in content_recommendations_for_user(
                user_id,
                prepared.train_interactions,
                content_index,
                top_n,
                excluded_threads_for_user(user_id, prepared.train_interactions, dataset.business.threads),
            )
        ]
        for user_id in user_ids
    }
    metric_key = selection.model_type
    metrics = evaluate_recommendation_sets(
        {metric_key: model_recommendations, "content_only": content_only, **baselines},
        prepared.test_interactions,
        set(dataset.business.threads.get_column("thread_id").to_list()),
        thread_categories(dataset.business.threads),
        popularity_by_thread(prepared.interactions),
        k=top_n,
    )
    return {
        "model_version": model_version,
        "model_type": metric_key,
        "model_trained": model.trained,
        "final_pipeline_model_type": metric_key,
        "final_pipeline_uses_winner": metric_key == selection.model_type,
        "normal_sources": sorted({source for items in generated.values() for _thread_id, _score, source in items}),
        "champion": selection_to_metrics(selection),
        "top_n": top_n,
        "metrics": metrics[metric_key],
        "baseline_comparison": metrics,
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
