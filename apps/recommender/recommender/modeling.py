from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from recommender.matrix import InteractionMatrix


@dataclass
class ModelResult:
    model: object | None
    model_type: str
    trained: bool
    hyperparameters: dict[str, object] | None = None


def recommend_for_user(
    model_result: ModelResult,
    interaction_matrix: InteractionMatrix,
    user_id: str,
    n: int,
    exclude_thread_ids: set[str] | None = None,
) -> list[tuple[str, float]]:
    exclude_thread_ids = exclude_thread_ids or set()
    if not model_result.trained or model_result.model is None:
        return []
    user_index = interaction_matrix.user_to_index.get(user_id)
    if user_index is None:
        return []

    ids, scores = model_result.model.recommend(
        user_index,
        interaction_matrix.matrix[user_index],
        N=max(n + len(exclude_thread_ids), n),
        filter_already_liked_items=True,
    )
    results: list[tuple[str, float]] = []
    for item_index, score in zip(ids, scores, strict=False):
        thread_id = interaction_matrix.index_to_thread.get(int(item_index))
        if not thread_id or thread_id in exclude_thread_ids:
            continue
        results.append((thread_id, float(score)))
        if len(results) >= n:
            break
    return results
