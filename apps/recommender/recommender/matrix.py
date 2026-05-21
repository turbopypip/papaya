from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import polars as pl
from scipy.sparse import csr_matrix


@dataclass
class InteractionMatrix:
    matrix: csr_matrix
    user_to_index: dict[str, int]
    thread_to_index: dict[str, int]
    index_to_user: dict[int, str]
    index_to_thread: dict[int, str]


def build_interaction_matrix(interactions: pl.DataFrame) -> InteractionMatrix:
    user_ids = sorted(interactions.get_column("user_id").unique().to_list()) if interactions.height else []
    thread_ids = sorted(interactions.get_column("thread_id").unique().to_list()) if interactions.height else []
    user_to_index = {user_id: idx for idx, user_id in enumerate(user_ids)}
    thread_to_index = {thread_id: idx for idx, thread_id in enumerate(thread_ids)}

    if interactions.is_empty():
        matrix = csr_matrix((0, 0), dtype=np.float32)
    else:
        rows = [user_to_index[user_id] for user_id in interactions.get_column("user_id").to_list()]
        cols = [thread_to_index[thread_id] for thread_id in interactions.get_column("thread_id").to_list()]
        data = interactions.get_column("score").cast(pl.Float32).to_numpy()
        matrix = csr_matrix((data, (rows, cols)), shape=(len(user_ids), len(thread_ids)), dtype=np.float32)

    return InteractionMatrix(
        matrix=matrix,
        user_to_index=user_to_index,
        thread_to_index=thread_to_index,
        index_to_user={idx: user_id for user_id, idx in user_to_index.items()},
        index_to_thread={idx: thread_id for thread_id, idx in thread_to_index.items()},
    )
