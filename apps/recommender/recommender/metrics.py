from __future__ import annotations

from collections.abc import Iterable
import math

import polars as pl


def _top_k(items: Iterable[str], k: int) -> list[str]:
    return list(items)[:k]


def recall_at_k(recommended: Iterable[str], relevant: set[str], k: int) -> float:
    if not relevant:
        return 0.0
    hits = len(set(_top_k(recommended, k)) & relevant)
    return hits / len(relevant)


def precision_at_k(recommended: Iterable[str], relevant: set[str], k: int) -> float:
    top = _top_k(recommended, k)
    if not top or k <= 0:
        return 0.0
    return len(set(top) & relevant) / min(k, len(top))


def hit_rate_at_k(recommended: Iterable[str], relevant: set[str], k: int) -> float:
    if not relevant:
        return 0.0
    return 1.0 if set(_top_k(recommended, k)) & relevant else 0.0


def ndcg_at_k(recommended: Iterable[str], relevant: set[str], k: int) -> float:
    if not relevant:
        return 0.0
    dcg = 0.0
    for index, item in enumerate(_top_k(recommended, k), start=1):
        if item in relevant:
            dcg += 1.0 / math.log2(index + 1)
    ideal_hits = min(len(relevant), k)
    idcg = sum(1.0 / math.log2(index + 1) for index in range(1, ideal_hits + 1))
    return dcg / idcg if idcg else 0.0


def map_at_k(recommended: Iterable[str], relevant: set[str], k: int) -> float:
    if not relevant:
        return 0.0
    hits = 0
    precision_sum = 0.0
    for index, item in enumerate(_top_k(recommended, k), start=1):
        if item in relevant:
            hits += 1
            precision_sum += hits / index
    return precision_sum / min(len(relevant), k)


def coverage(recommendations_by_user: dict[str, list[str]], all_thread_ids: set[str]) -> float:
    if not all_thread_ids:
        return 0.0
    recommended = {thread_id for recs in recommendations_by_user.values() for thread_id in recs}
    return len(recommended & all_thread_ids) / len(all_thread_ids)


def diversity(recommended: list[str], thread_categories: dict[str, set[str]]) -> float:
    if len(recommended) < 2:
        return 0.0
    pairs = 0
    dissimilarity = 0.0
    for left_index, left in enumerate(recommended):
        for right in recommended[left_index + 1 :]:
            left_categories = thread_categories.get(left, set())
            right_categories = thread_categories.get(right, set())
            union = left_categories | right_categories
            similarity = len(left_categories & right_categories) / len(union) if union else 0.0
            dissimilarity += 1.0 - similarity
            pairs += 1
    return dissimilarity / pairs if pairs else 0.0


def novelty(recommended: list[str], popularity: dict[str, float]) -> float:
    if not recommended:
        return 0.0
    total = sum(popularity.values()) or 1.0
    scores = []
    for thread_id in recommended:
        probability = max(popularity.get(thread_id, 0.0) / total, 1e-12)
        scores.append(-math.log2(probability))
    return sum(scores) / len(scores)


def personalization_score(recommendations_by_user: dict[str, list[str]], k: int = 10) -> float:
    users = sorted(recommendations_by_user)
    if len(users) < 2:
        return 0.0
    distances = []
    for left_index, left_user in enumerate(users):
        left = set(_top_k(recommendations_by_user.get(left_user, []), k))
        for right_user in users[left_index + 1 :]:
            right = set(_top_k(recommendations_by_user.get(right_user, []), k))
            union = left | right
            similarity = len(left & right) / len(union) if union else 0.0
            distances.append(1.0 - similarity)
    return sum(distances) / len(distances) if distances else 0.0


def ranking_report(
    recommendations_by_user: dict[str, list[str]],
    relevant_by_user: dict[str, set[str]],
    all_thread_ids: set[str],
    thread_categories: dict[str, set[str]] | None = None,
    popularity: dict[str, float] | None = None,
    k: int = 10,
) -> dict[str, float]:
    users = sorted(set(recommendations_by_user) | set(relevant_by_user))
    if not users:
        return {
            "precision_at_k": 0.0,
            "recall_at_k": 0.0,
            "ndcg_at_k": 0.0,
            "map_at_k": 0.0,
            "hit_rate_at_k": 0.0,
            "coverage": 0.0,
            "diversity": 0.0,
            "novelty": 0.0,
            "personalization": 0.0,
        }

    precisions = []
    recalls = []
    ndcgs = []
    maps = []
    hit_rates = []
    diversities = []
    novelties = []
    for user_id in users:
        recs = recommendations_by_user.get(user_id, [])
        relevant = relevant_by_user.get(user_id, set())
        precisions.append(precision_at_k(recs, relevant, k))
        recalls.append(recall_at_k(recs, relevant, k))
        ndcgs.append(ndcg_at_k(recs, relevant, k))
        maps.append(map_at_k(recs, relevant, k))
        hit_rates.append(hit_rate_at_k(recs, relevant, k))
        if thread_categories is not None:
            diversities.append(diversity(recs[:k], thread_categories))
        if popularity is not None:
            novelties.append(novelty(recs[:k], popularity))

    return {
        "precision_at_k": sum(precisions) / len(precisions),
        "recall_at_k": sum(recalls) / len(recalls),
        "ndcg_at_k": sum(ndcgs) / len(ndcgs),
        "map_at_k": sum(maps) / len(maps),
        "hit_rate_at_k": sum(hit_rates) / len(hit_rates),
        "coverage": coverage(recommendations_by_user, all_thread_ids),
        "diversity": sum(diversities) / len(diversities) if diversities else 0.0,
        "novelty": sum(novelties) / len(novelties) if novelties else 0.0,
        "personalization": personalization_score(recommendations_by_user, k),
    }


def recommendation_daily_quality(recommendation_daily: pl.DataFrame) -> dict[str, float]:
    if recommendation_daily.is_empty():
        return {
            "recommendation_impressions": 0.0,
            "recommendation_clicks": 0.0,
            "recommendation_ctr": 0.0,
            "recommendation_avg_position": 0.0,
        }
    impressions = float(recommendation_daily.get_column("impressions").sum() or 0.0)
    clicks = float(recommendation_daily.get_column("clicks").sum() or 0.0)
    position_weight = float((recommendation_daily.get_column("impressions") * recommendation_daily.get_column("avg_position")).sum() or 0.0)
    return {
        "recommendation_impressions": impressions,
        "recommendation_clicks": clicks,
        "recommendation_ctr": clicks / impressions if impressions else 0.0,
        "recommendation_avg_position": position_weight / impressions if impressions else 0.0,
    }
