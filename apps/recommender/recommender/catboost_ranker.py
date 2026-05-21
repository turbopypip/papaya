from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
import math
import random
import re
from typing import Any

import polars as pl

from recommender.data import BusinessData, normalize_datetime_columns
from recommender.metrics import ranking_report
from recommender.recommendations import excluded_threads_for_user


MODEL_TYPE = "catboost_ranker"
FEATURE_SCHEMA_VERSION = "catboost_ranker_features_v1"
MISSING_CATEGORY = "__missing__"

TOKEN_RE = re.compile(r"[a-zA-Z0-9_+#.-]{2,}")


@dataclass(frozen=True)
class FeatureSchema:
    version: str
    numeric_features: list[str]
    categorical_features: list[str]

    @property
    def feature_names(self) -> list[str]:
        return [*self.numeric_features, *self.categorical_features]

    @property
    def categorical_indices(self) -> list[int]:
        offset = len(self.numeric_features)
        return list(range(offset, offset + len(self.categorical_features)))


@dataclass
class CatBoostRankerArtifact:
    model: Any
    feature_schema: FeatureSchema
    trained: bool
    hyperparameters: dict[str, object] = field(default_factory=dict)


DEFAULT_FEATURE_SCHEMA = FeatureSchema(
    version=FEATURE_SCHEMA_VERSION,
    numeric_features=[
        "user_total_score",
        "user_events_count",
        "user_unique_threads",
        "user_view_count",
        "user_like_count",
        "user_comment_count",
        "user_post_count",
        "user_click_count",
        "user_activity_strength",
        "user_recency_days",
        "thread_age_days",
        "thread_freshness",
        "thread_title_length",
        "thread_content_length",
        "thread_post_count",
        "thread_comment_count",
        "thread_like_count",
        "thread_popularity_score",
        "thread_activity_score",
        "thread_unique_users",
        "thread_view_count",
        "thread_click_count",
        "pair_category_overlap",
        "pair_category_jaccard",
        "pair_token_overlap",
        "pair_token_jaccard",
        "pair_author_affinity",
        "pair_seen_flag",
        "pair_clicked_flag",
        "pair_liked_flag",
        "pair_commented_flag",
        "pair_affinity_score",
        "pair_recency_affinity",
    ],
    categorical_features=[
        "thread_primary_category",
        "thread_category_signature",
        "thread_author_user_id",
        "user_primary_category",
    ],
)


def train_catboost_ranker(
    business: BusinessData,
    train_interactions: pl.DataFrame,
    *,
    random_state: int,
    top_n: int,
) -> CatBoostRankerArtifact:
    from catboost import CatBoostRanker, Pool

    rows, labels, group_ids = build_training_rows(
        business,
        train_interactions,
        random_state=random_state,
        negatives_per_positive=4,
    )
    model_params: dict[str, object] = {
        "loss_function": "YetiRank",
        "iterations": 160,
        "depth": 6,
        "learning_rate": 0.08,
        "random_seed": random_state,
        "allow_writing_files": False,
        "verbose": False,
    }
    params: dict[str, object] = {
        **model_params,
        "score_direction": "negated_catboost_prediction",
    }
    if not rows:
        return CatBoostRankerArtifact(
            model=None,
            feature_schema=DEFAULT_FEATURE_SCHEMA,
            trained=False,
            hyperparameters={**params, "reason": "not_enough_training_pairs", "top_n": top_n},
        )

    frame = rows_to_pandas(rows, DEFAULT_FEATURE_SCHEMA)
    pool = Pool(
        frame,
        label=labels,
        group_id=group_ids,
        cat_features=DEFAULT_FEATURE_SCHEMA.categorical_features,
        feature_names=DEFAULT_FEATURE_SCHEMA.feature_names,
    )
    model = CatBoostRanker(**model_params)
    model.fit(pool)
    return CatBoostRankerArtifact(
        model=model,
        feature_schema=DEFAULT_FEATURE_SCHEMA,
        trained=True,
        hyperparameters={**params, "top_n": top_n, "training_rows": len(rows), "training_groups": len(set(group_ids))},
    )


def build_training_rows(
    business: BusinessData,
    interactions: pl.DataFrame,
    *,
    random_state: int,
    negatives_per_positive: int,
) -> tuple[list[dict[str, object]], list[float], list[str]]:
    if business.threads.is_empty() or interactions.is_empty():
        return [], [], []

    rng = random.Random(random_state)
    catalog_thread_ids = set(business.threads.get_column("thread_id").to_list())
    interactions = interactions.filter(pl.col("thread_id").is_in(catalog_thread_ids))
    if interactions.is_empty():
        return [], [], []

    max_score = float(interactions.get_column("score").max() or 1.0)
    rows: list[dict[str, object]] = []
    labels: list[float] = []
    group_ids: list[str] = []
    positive_by_user: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for row in interactions.select("user_id", "thread_id", "score").iter_rows(named=True):
        positive_by_user[str(row["user_id"])].append((str(row["thread_id"]), max(float(row["score"]), 0.01)))

    all_thread_ids = sorted(catalog_thread_ids)
    for user_id in sorted(positive_by_user):
        positives = positive_by_user[user_id]
        positive_ids = {thread_id for thread_id, _score in positives}
        negative_pool = [thread_id for thread_id in all_thread_ids if thread_id not in positive_ids]
        if not negative_pool:
            continue
        rng.shuffle(negative_pool)
        negative_count = min(len(negative_pool), max(len(positives) * negatives_per_positive, 1))
        candidate_ids = [thread_id for thread_id, _score in positives] + negative_pool[:negative_count]
        feature_rows = build_feature_rows(business, interactions, user_id, candidate_ids)
        feature_by_thread = {str(row["thread_id"]): row["features"] for row in feature_rows}
        group_start = len(rows)
        for thread_id, score in positives:
            features = feature_by_thread.get(thread_id)
            if features is None:
                continue
            rows.append(features)
            labels.append(min(float(score) / max(max_score, 1.0), 1.0))
            group_ids.append(user_id)
        for thread_id in negative_pool[:negative_count]:
            features = feature_by_thread.get(thread_id)
            if features is None:
                continue
            rows.append(features)
            labels.append(0.0)
            group_ids.append(user_id)
        if len(rows) - group_start < 2:
            del rows[group_start:]
            del labels[group_start:]
            del group_ids[group_start:]

    return rows, labels, group_ids


def recommend_with_catboost(
    artifact: CatBoostRankerArtifact,
    business: BusinessData,
    interactions: pl.DataFrame,
    user_id: str,
    *,
    limit: int,
    candidate_pool_size: int,
    min_model_interactions: int,
) -> list[tuple[str, float]]:
    if not artifact.trained or artifact.model is None or business.threads.is_empty():
        return []
    if user_feature_signal(interactions, user_id) < float(min_model_interactions):
        return []

    catalog_thread_ids = set(business.threads.get_column("thread_id").to_list())
    interactions = interactions.filter(pl.col("thread_id").is_in(catalog_thread_ids)) if interactions.height else interactions
    exclude = excluded_threads_for_user(user_id, interactions, business.threads)
    candidate_ids = [
        str(thread_id)
        for thread_id in business.threads.get_column("thread_id").to_list()
        if str(thread_id) in catalog_thread_ids and str(thread_id) not in exclude
    ]
    if not candidate_ids:
        return []

    feature_rows = build_feature_rows(business, interactions, user_id, candidate_ids)
    if not feature_rows:
        return []
    frame = rows_to_pandas([row["features"] for row in feature_rows], artifact.feature_schema)
    scores = predict_scores(artifact, frame)
    ranked = sorted(
        zip((str(row["thread_id"]) for row in feature_rows), scores, strict=True),
        key=lambda item: item[1],
        reverse=True,
    )
    return [(thread_id, float(score)) for thread_id, score in ranked[:limit]]


def evaluate_catboost_ranker(
    artifact: CatBoostRankerArtifact,
    business: BusinessData,
    train_interactions: pl.DataFrame,
    test_interactions: pl.DataFrame,
    *,
    top_n: int,
    candidate_pool_size: int,
    min_model_interactions: int,
    k: int,
) -> dict[str, float]:
    if test_interactions.is_empty() or business.threads.is_empty():
        return _empty_metrics()

    relevant_by_user = {
        _group_key(user_id): set(group.get_column("thread_id").to_list())
        for user_id, group in test_interactions.group_by("user_id")
    }
    sampled_recommendations_by_user: dict[str, list[str]] = {}
    full_catalog_recommendations_by_user: dict[str, list[str]] = {}
    candidate_counts: list[float] = []
    positive_counts: list[float] = []
    positive_scores: list[float] = []
    negative_scores: list[float] = []
    auc_pairs = 0
    auc_wins = 0.0
    catalog_thread_ids = {str(thread_id) for thread_id in business.threads.get_column("thread_id").to_list()}
    train_interactions = train_interactions.filter(pl.col("thread_id").is_in(catalog_thread_ids)) if train_interactions.height else train_interactions
    for user_id in sorted(relevant_by_user):
        full_catalog_items = recommend_with_catboost(
            artifact,
            business,
            train_interactions,
            str(user_id),
            limit=top_n,
            candidate_pool_size=candidate_pool_size,
            min_model_interactions=min_model_interactions,
        )
        full_catalog_recommendations_by_user[str(user_id)] = [thread_id for thread_id, _score in full_catalog_items]

        positives = sorted(relevant_by_user[user_id] & catalog_thread_ids)
        if not positives or user_feature_signal(train_interactions, str(user_id)) < float(min_model_interactions):
            sampled_recommendations_by_user[str(user_id)] = []
            continue

        exclude = excluded_threads_for_user(str(user_id), train_interactions, business.threads)
        negative_pool = sorted(catalog_thread_ids - set(positives) - exclude)
        rng = random.Random(f"catboost-eval:{user_id}")
        rng.shuffle(negative_pool)
        negatives = negative_pool[: max(candidate_pool_size, k)]
        candidate_ids = list(dict.fromkeys([*positives, *negatives]))
        feature_rows = build_feature_rows(business, train_interactions, str(user_id), candidate_ids)
        if not feature_rows or artifact.model is None or not artifact.trained:
            sampled_recommendations_by_user[str(user_id)] = []
            continue

        frame = rows_to_pandas([row["features"] for row in feature_rows], artifact.feature_schema)
        scores = predict_scores(artifact, frame)
        scored = [(str(row["thread_id"]), float(score)) for row, score in zip(feature_rows, scores, strict=True)]
        sampled_recommendations_by_user[str(user_id)] = [
            thread_id for thread_id, _score in sorted(scored, key=lambda item: item[1], reverse=True)[:top_n]
        ]
        candidate_counts.append(float(len(candidate_ids)))
        positive_counts.append(float(len(positives)))
        positives_set = set(positives)
        user_positive_scores = [score for thread_id, score in scored if thread_id in positives_set]
        user_negative_scores = [score for thread_id, score in scored if thread_id not in positives_set]
        positive_scores.extend(user_positive_scores)
        negative_scores.extend(user_negative_scores)
        for pos_score in user_positive_scores:
            for neg_score in user_negative_scores:
                auc_pairs += 1
                if pos_score > neg_score:
                    auc_wins += 1.0
                elif pos_score == neg_score:
                    auc_wins += 0.5

    categories = {
        str(row["thread_id"]): set(_categories(row.get("categories")))
        for row in business.threads.iter_rows(named=True)
    }
    popularity = (
        dict(train_interactions.group_by("thread_id").agg(pl.sum("score").alias("score")).iter_rows())
        if train_interactions.height
        else {}
    )
    metrics = ranking_report(
        sampled_recommendations_by_user,
        relevant_by_user,
        set(business.threads.get_column("thread_id").to_list()) if business.threads.height else set(),
        categories,
        {str(thread_id): float(score) for thread_id, score in popularity.items()},
        k=k,
    )
    full_catalog_metrics = ranking_report(
        full_catalog_recommendations_by_user,
        relevant_by_user,
        set(business.threads.get_column("thread_id").to_list()) if business.threads.height else set(),
        categories,
        {str(thread_id): float(score) for thread_id, score in popularity.items()},
        k=k,
    )
    metrics["catboost_ranker_score"] = (
        0.45 * metrics["ndcg_at_k"]
        + 0.25 * metrics["recall_at_k"]
        + 0.15 * metrics["map_at_k"]
        + 0.10 * metrics["coverage"]
        + 0.05 * metrics["diversity"]
    )
    metrics.update(
        {
            "evaluation_users": float(len(relevant_by_user)),
            "evaluation_candidate_threads": float(sum(candidate_counts)),
            "evaluation_positive_threads": float(sum(positive_counts)),
            "evaluation_avg_candidates_per_user": _mean(candidate_counts),
            "evaluation_avg_positives_per_user": _mean(positive_counts),
            "score_positive_mean": _mean(positive_scores),
            "score_positive_p50": _quantile(positive_scores, 0.50),
            "score_positive_min": min(positive_scores) if positive_scores else 0.0,
            "score_positive_max": max(positive_scores) if positive_scores else 0.0,
            "score_negative_mean": _mean(negative_scores),
            "score_negative_p50": _quantile(negative_scores, 0.50),
            "score_negative_min": min(negative_scores) if negative_scores else 0.0,
            "score_negative_max": max(negative_scores) if negative_scores else 0.0,
            "score_margin_mean": _mean(positive_scores) - _mean(negative_scores),
            "pairwise_auc": auc_wins / auc_pairs if auc_pairs else 0.0,
        }
    )
    for name, value in full_catalog_metrics.items():
        metrics[f"full_catalog_{name}"] = value
    return metrics


def generate_catboost_for_users(
    user_ids: list[str],
    business: BusinessData,
    interactions: pl.DataFrame,
    artifact: CatBoostRankerArtifact,
    *,
    top_n: int,
    candidate_pool_size: int,
    min_model_interactions: int,
) -> dict[str, list[tuple[str, float, str]]]:
    from recommender.baselines import category_popular, latest_active, popular_recent, thread_affinity_recent
    from recommender.recommendations import _fallback_source, _merge_ranked_sources

    catalog_thread_ids = set(business.threads.get_column("thread_id").to_list()) if business.threads.height else set()
    if not catalog_thread_ids:
        return {user_id: [] for user_id in user_ids}
    interactions = interactions.filter(pl.col("thread_id").is_in(catalog_thread_ids)) if interactions.height else interactions
    popular = popular_recent(interactions, limit=candidate_pool_size)
    latest = latest_active(business.threads, interactions, limit=candidate_pool_size)
    output: dict[str, list[tuple[str, float, str]]] = {}
    for user_id in user_ids:
        model_items = recommend_with_catboost(
            artifact,
            business,
            interactions,
            user_id,
            limit=top_n,
            candidate_pool_size=candidate_pool_size,
            min_model_interactions=min_model_interactions,
        )
        if model_items:
            output[user_id] = [(thread_id, score, "model") for thread_id, score in model_items]
            continue

        exclude = excluded_threads_for_user(user_id, interactions, business.threads)
        fallback_items = _merge_ranked_sources(
            [
                ("thread_affinity_recent", thread_affinity_recent(user_id, business.threads, interactions, limit=candidate_pool_size)),
                ("category_popular", category_popular(user_id, business.threads, interactions, limit=candidate_pool_size)),
                ("popular_recent", popular),
                ("latest_active", latest),
            ],
            exclude,
            top_n,
        )
        output[user_id] = [(thread_id, score, _fallback_source(source)) for thread_id, score, source in fallback_items]
    return output


def build_feature_rows(
    business: BusinessData,
    interactions: pl.DataFrame,
    user_id: str,
    candidate_thread_ids: list[str],
    now: datetime | None = None,
) -> list[dict[str, object]]:
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    users = normalize_datetime_columns(business.users, ["created_at"])
    threads = normalize_datetime_columns(business.threads, ["created_at", "updated_at"])
    posts = normalize_datetime_columns(business.posts, ["created_at", "updated_at"])
    comments = normalize_datetime_columns(business.comments, ["created_at", "updated_at"])
    likes = normalize_datetime_columns(business.likes, ["created_at"])
    interactions = normalize_datetime_columns(interactions, ["last_event_at"]) if interactions.height else interactions

    user_stats = _user_stats(user_id, interactions, threads)
    thread_stats = _thread_stats(interactions, posts, comments, likes)
    thread_rows = {str(row["thread_id"]): row for row in threads.iter_rows(named=True)}
    output: list[dict[str, object]] = []
    for thread_id in candidate_thread_ids:
        row = thread_rows.get(str(thread_id))
        if row is None:
            continue
        features = _features_for_pair(user_id, row, user_stats, thread_stats.get(str(thread_id), {}), now)
        output.append({"thread_id": str(thread_id), "features": features})
    return output


def rows_to_pandas(rows: list[dict[str, object]], schema: FeatureSchema):
    import pandas as pd

    normalized = []
    for row in rows:
        normalized.append(
            {
                **{name: float(row.get(name, 0.0) or 0.0) for name in schema.numeric_features},
                **{name: str(row.get(name) or MISSING_CATEGORY) for name in schema.categorical_features},
            }
        )
    return pd.DataFrame(normalized, columns=schema.feature_names)


def predict_scores(artifact: CatBoostRankerArtifact, frame) -> list[float]:
    from catboost import Pool

    pool = Pool(
        frame,
        cat_features=artifact.feature_schema.categorical_features,
        feature_names=artifact.feature_schema.feature_names,
    )
    return [-float(score) for score in artifact.model.predict(pool)]


def user_feature_signal(interactions: pl.DataFrame, user_id: str) -> float:
    if interactions.is_empty() or "user_id" not in interactions.columns:
        return 0.0
    rows = interactions.filter(pl.col("user_id") == user_id)
    if rows.is_empty():
        return 0.0
    signal_columns = [
        "thread_viewed_count",
        "like_count",
        "recommendation_clicked_count",
        "post_created_count",
        "comment_created_count",
    ]
    available = [column for column in signal_columns if column in rows.columns]
    if available:
        return float(sum(rows.get_column(column).sum() or 0.0 for column in available))
    return float(rows.get_column("events_count").sum() or 0.0)


def _features_for_pair(
    user_id: str,
    thread: dict[str, object],
    user_stats: dict[str, object],
    thread_stats: dict[str, float],
    now: datetime,
) -> dict[str, object]:
    thread_id = str(thread["thread_id"])
    categories = set(_categories(thread.get("categories")))
    user_categories: Counter[str] = user_stats["categories"]  # type: ignore[assignment]
    user_tokens: Counter[str] = user_stats["tokens"]  # type: ignore[assignment]
    title = str(thread.get("title") or "")
    content = str(thread.get("content") or "")
    thread_tokens = set(_tokens(f"{title} {content}"))
    shared_categories = categories & set(user_categories)
    shared_tokens = thread_tokens & set(user_tokens)
    age_days = _age_days(thread.get("created_at"), now)
    user_recency = float(user_stats.get("recency_days", 3650.0))
    affinity = float(user_stats.get("thread_scores", {}).get(thread_id, 0.0))  # type: ignore[union-attr]
    return {
        "user_total_score": float(user_stats.get("total_score", 0.0)),
        "user_events_count": float(user_stats.get("events_count", 0.0)),
        "user_unique_threads": float(user_stats.get("unique_threads", 0.0)),
        "user_view_count": float(user_stats.get("view_count", 0.0)),
        "user_like_count": float(user_stats.get("like_count", 0.0)),
        "user_comment_count": float(user_stats.get("comment_count", 0.0)),
        "user_post_count": float(user_stats.get("post_count", 0.0)),
        "user_click_count": float(user_stats.get("click_count", 0.0)),
        "user_activity_strength": math.log1p(float(user_stats.get("events_count", 0.0))),
        "user_recency_days": user_recency,
        "thread_age_days": age_days,
        "thread_freshness": 1.0 / (1.0 + age_days),
        "thread_title_length": float(len(title)),
        "thread_content_length": float(len(content)),
        "thread_post_count": float(thread_stats.get("post_count", 0.0)),
        "thread_comment_count": float(thread_stats.get("comment_count", 0.0)),
        "thread_like_count": float(thread_stats.get("like_count", 0.0)),
        "thread_popularity_score": float(thread_stats.get("score", 0.0)),
        "thread_activity_score": math.log1p(float(thread_stats.get("events_count", 0.0))),
        "thread_unique_users": float(thread_stats.get("unique_users", 0.0)),
        "thread_view_count": float(thread_stats.get("view_count", 0.0)),
        "thread_click_count": float(thread_stats.get("click_count", 0.0)),
        "pair_category_overlap": float(len(shared_categories)),
        "pair_category_jaccard": _jaccard(categories, set(user_categories)),
        "pair_token_overlap": float(len(shared_tokens)),
        "pair_token_jaccard": _jaccard(thread_tokens, set(user_tokens)),
        "pair_author_affinity": 1.0 if str(thread.get("author_user_id") or "") in user_stats.get("authors", set()) else 0.0,
        "pair_seen_flag": 1.0 if thread_id in user_stats.get("viewed_threads", set()) else 0.0,
        "pair_clicked_flag": 1.0 if thread_id in user_stats.get("clicked_threads", set()) else 0.0,
        "pair_liked_flag": 1.0 if thread_id in user_stats.get("liked_threads", set()) else 0.0,
        "pair_commented_flag": 1.0 if thread_id in user_stats.get("commented_threads", set()) else 0.0,
        "pair_affinity_score": affinity,
        "pair_recency_affinity": affinity / (1.0 + user_recency),
        "thread_primary_category": sorted(categories)[0] if categories else MISSING_CATEGORY,
        "thread_category_signature": "|".join(sorted(categories)) if categories else MISSING_CATEGORY,
        "thread_author_user_id": str(thread.get("author_user_id") or MISSING_CATEGORY),
        "user_primary_category": user_categories.most_common(1)[0][0] if user_categories else MISSING_CATEGORY,
    }


def _user_stats(user_id: str, interactions: pl.DataFrame, threads: pl.DataFrame) -> dict[str, object]:
    stats: dict[str, object] = {
        "categories": Counter(),
        "tokens": Counter(),
        "authors": set(),
        "thread_scores": {},
        "viewed_threads": set(),
        "clicked_threads": set(),
        "liked_threads": set(),
        "commented_threads": set(),
        "total_score": 0.0,
        "events_count": 0.0,
        "unique_threads": 0.0,
        "view_count": 0.0,
        "like_count": 0.0,
        "comment_count": 0.0,
        "post_count": 0.0,
        "click_count": 0.0,
        "recency_days": 3650.0,
    }
    if interactions.is_empty():
        return stats

    thread_rows = {str(row["thread_id"]): row for row in threads.iter_rows(named=True)}
    rows = interactions.filter(pl.col("user_id") == user_id)
    if rows.is_empty():
        return stats

    stats["total_score"] = float(rows.get_column("score").sum() or 0.0)
    stats["events_count"] = float(rows.get_column("events_count").sum() or 0.0)
    stats["unique_threads"] = float(rows.get_column("thread_id").n_unique())
    for source, target in [
        ("thread_viewed_count", "view_count"),
        ("like_count", "like_count"),
        ("recommendation_clicked_count", "click_count"),
        ("comment_created_count", "comment_count"),
        ("post_created_count", "post_count"),
    ]:
        if source in rows.columns:
            stats[target] = float(rows.get_column(source).sum() or 0.0)
    if "last_event_at" in rows.columns:
        latest = rows.get_column("last_event_at").max()
        stats["recency_days"] = _age_days(latest, datetime.now(timezone.utc).replace(tzinfo=None))
    thread_scores: dict[str, float] = {}
    for row in rows.iter_rows(named=True):
        thread_id = str(row["thread_id"])
        score = float(row.get("score") or 0.0)
        thread_scores[thread_id] = score
        thread = thread_rows.get(thread_id)
        if thread is not None:
            stats["categories"].update({category: score for category in _categories(thread.get("categories"))})  # type: ignore[union-attr]
            stats["tokens"].update({token: score for token in _tokens(f"{thread.get('title') or ''} {thread.get('content') or ''}")})  # type: ignore[union-attr]
            if thread.get("author_user_id"):
                stats["authors"].add(str(thread["author_user_id"]))  # type: ignore[union-attr]
        if float(row.get("thread_viewed_count") or 0.0) > 0:
            stats["viewed_threads"].add(thread_id)  # type: ignore[union-attr]
        if float(row.get("recommendation_clicked_count") or 0.0) > 0:
            stats["clicked_threads"].add(thread_id)  # type: ignore[union-attr]
        if float(row.get("like_count") or 0.0) > 0:
            stats["liked_threads"].add(thread_id)  # type: ignore[union-attr]
        if float(row.get("comment_created_count") or 0.0) > 0:
            stats["commented_threads"].add(thread_id)  # type: ignore[union-attr]
    stats["thread_scores"] = thread_scores
    return stats


def _thread_stats(interactions: pl.DataFrame, posts: pl.DataFrame, comments: pl.DataFrame, likes: pl.DataFrame) -> dict[str, dict[str, float]]:
    stats: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    if interactions.height:
        aggregations = [
            pl.sum("score").alias("score"),
            pl.sum("events_count").alias("events_count"),
            pl.col("user_id").n_unique().alias("unique_users"),
        ]
        for column, alias in [
            ("thread_viewed_count", "view_count"),
            ("recommendation_clicked_count", "click_count"),
        ]:
            if column in interactions.columns:
                aggregations.append(pl.sum(column).alias(alias))
        for row in interactions.group_by("thread_id").agg(aggregations).iter_rows(named=True):
            stats[str(row["thread_id"])].update({key: float(value or 0.0) for key, value in row.items() if key != "thread_id"})
    if posts.height:
        for thread_id, count in posts.group_by("thread_id").len().iter_rows():
            stats[str(thread_id)]["post_count"] = float(count)
    if comments.height:
        for thread_id, count in comments.group_by("thread_id").len().iter_rows():
            stats[str(thread_id)]["comment_count"] = float(count)
    if likes.height:
        for thread_id, count in likes.group_by("thread_id").len().iter_rows():
            stats[str(thread_id)]["like_count"] = float(count)
    return {thread_id: dict(values) for thread_id, values in stats.items()}


def _empty_metrics() -> dict[str, float]:
    metrics = ranking_report({}, {}, set(), k=10)
    metrics["catboost_ranker_score"] = 0.0
    return metrics


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _quantile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(max(int(round((len(ordered) - 1) * q)), 0), len(ordered) - 1)
    return ordered[index]


def _group_key(value: object) -> str:
    if isinstance(value, tuple):
        return str(value[0]) if value else ""
    return str(value)


def _categories(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip().lower() for item in value if str(item).strip()]
    return [part.strip().lower() for part in str(value).split(",") if part.strip()]


def _tokens(value: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(value)]


def _jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 0.0


def _age_days(value: object, now: datetime) -> float:
    if value is None:
        return 3650.0
    if hasattr(value, "to_pydatetime"):
        value = value.to_pydatetime()
    if not isinstance(value, datetime):
        return 3650.0
    value = value.replace(tzinfo=None) if value.tzinfo else value
    return max((now - value).total_seconds() / 86400.0, 0.0)
