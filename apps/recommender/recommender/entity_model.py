from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import math
import random

import numpy as np
import polars as pl
from scipy import sparse
from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.linear_model import SGDClassifier
from sklearn.decomposition import TruncatedSVD

from recommender.content import thread_documents
from recommender.matrix import InteractionMatrix
from recommender.modeling import ModelResult


TEXT_FEATURES = 384
MAX_NEGATIVES_PER_USER = 80


@dataclass
class EntityFeatureRecommender:
    classifier: SGDClassifier
    user_to_index: dict[str, int]
    thread_to_index: dict[str, int]
    index_to_thread: dict[int, str]
    user_text: sparse.csr_matrix
    user_categories: sparse.csr_matrix
    user_numeric: np.ndarray
    thread_text: sparse.csr_matrix
    thread_categories: sparse.csr_matrix
    thread_numeric: np.ndarray
    hyperparameters: dict[str, object]

    uses_thread_features: bool = True

    def recommend(self, user_index, user_items, N, filter_already_liked_items=True):
        if user_index < 0 or user_index >= self.user_text.shape[0]:
            return np.array([], dtype=np.int64), np.array([], dtype=np.float32)

        scores = self.score_user_index(user_index)
        if filter_already_liked_items:
            scores[user_items.indices] = -np.inf
        if scores.size == 0:
            return np.array([], dtype=np.int64), np.array([], dtype=np.float32)

        candidate_count = min(int(N), scores.size)
        positions = np.argpartition(-scores, range(candidate_count))[:candidate_count]
        ordered = positions[np.argsort(-scores[positions])]
        ordered = ordered[np.isfinite(scores[ordered])]
        return ordered.astype(np.int64), scores[ordered].astype(np.float32)

    def score_user_index(self, user_index: int) -> np.ndarray:
        pair_features = _pair_features_for_user(
            user_index,
            self.user_text,
            self.user_categories,
            self.user_numeric,
            self.thread_text,
            self.thread_categories,
            self.thread_numeric,
        )
        if hasattr(self.classifier, "predict_proba"):
            return self.classifier.predict_proba(pair_features)[:, 1].astype(np.float32)
        return self.classifier.decision_function(pair_features).astype(np.float32)


@dataclass
class FeatureAwareFactorizationRecommender:
    latent_scores: np.ndarray
    user_to_index: dict[str, int]
    thread_to_index: dict[str, int]
    index_to_thread: dict[int, str]
    user_text: sparse.csr_matrix
    user_categories: sparse.csr_matrix
    user_numeric: np.ndarray
    thread_text: sparse.csr_matrix
    thread_categories: sparse.csr_matrix
    thread_numeric: np.ndarray
    hyperparameters: dict[str, object]

    uses_thread_features: bool = True

    def recommend(self, user_index, user_items, N, filter_already_liked_items=True):
        if user_index < 0 or user_index >= self.latent_scores.shape[0]:
            return np.array([], dtype=np.int64), np.array([], dtype=np.float32)
        scores = self.score_user_index(user_index)
        if filter_already_liked_items:
            scores[user_items.indices] = -np.inf
        if scores.size == 0:
            return np.array([], dtype=np.int64), np.array([], dtype=np.float32)
        candidate_count = min(int(N), scores.size)
        positions = np.argpartition(-scores, range(candidate_count))[:candidate_count]
        ordered = positions[np.argsort(-scores[positions])]
        ordered = ordered[np.isfinite(scores[ordered])]
        return ordered.astype(np.int64), scores[ordered].astype(np.float32)

    def score_user_index(self, user_index: int) -> np.ndarray:
        text_similarity = np.asarray(self.user_text[user_index].dot(self.thread_text.T).todense()).ravel()
        if self.thread_categories.shape[1]:
            category_similarity = np.asarray(self.user_categories[user_index].dot(self.thread_categories.T).todense()).ravel()
        else:
            category_similarity = np.zeros(self.thread_text.shape[0], dtype=np.float32)
        numeric_affinity = self.thread_numeric @ self.user_numeric[user_index, : self.thread_numeric.shape[1]]
        scores = (
            0.70 * _normalize_vector(self.latent_scores[user_index])
            + 0.18 * _normalize_vector(text_similarity)
            + 0.08 * _normalize_vector(category_similarity)
            + 0.04 * _normalize_vector(numeric_affinity)
        )
        return scores.astype(np.float32)


@dataclass
class TwoTowerDotRecommender:
    user_vectors: np.ndarray
    thread_vectors: np.ndarray
    user_to_index: dict[str, int]
    thread_to_index: dict[str, int]
    index_to_thread: dict[int, str]
    hyperparameters: dict[str, object]

    uses_thread_features: bool = True

    def recommend(self, user_index, user_items, N, filter_already_liked_items=True):
        if user_index < 0 or user_index >= self.user_vectors.shape[0]:
            return np.array([], dtype=np.int64), np.array([], dtype=np.float32)
        scores = self.score_user_index(user_index)
        if filter_already_liked_items:
            scores[user_items.indices] = -np.inf
        if scores.size == 0:
            return np.array([], dtype=np.int64), np.array([], dtype=np.float32)
        candidate_count = min(int(N), scores.size)
        positions = np.argpartition(-scores, range(candidate_count))[:candidate_count]
        ordered = positions[np.argsort(-scores[positions])]
        ordered = ordered[np.isfinite(scores[ordered])]
        return ordered.astype(np.int64), scores[ordered].astype(np.float32)

    def score_user_index(self, user_index: int) -> np.ndarray:
        return (self.thread_vectors @ self.user_vectors[user_index]).astype(np.float32)


def train_entity_feature_model(
    threads: pl.DataFrame,
    interactions: pl.DataFrame,
    interaction_matrix: InteractionMatrix,
    random_state: int = 42,
) -> ModelResult:
    return _train_pair_feature_classifier(
        threads,
        interactions,
        interaction_matrix,
        random_state=random_state,
        model_type="entity_feature_sgd",
        loss="log_loss",
        alpha=0.0001,
        max_iter=1000,
        ranking_weights=False,
    )


def train_learning_to_rank_model(
    threads: pl.DataFrame,
    interactions: pl.DataFrame,
    interaction_matrix: InteractionMatrix,
    random_state: int = 42,
) -> ModelResult:
    return _train_pair_feature_classifier(
        threads,
        interactions,
        interaction_matrix,
        random_state=random_state,
        model_type="learning_to_rank_sgd",
        loss="modified_huber",
        alpha=0.00005,
        max_iter=1200,
        ranking_weights=True,
    )


def train_factorization_machine_model(
    threads: pl.DataFrame,
    interactions: pl.DataFrame,
    interaction_matrix: InteractionMatrix,
    random_state: int = 42,
) -> ModelResult:
    if interactions.is_empty() or interaction_matrix.matrix.nnz == 0 or min(interaction_matrix.matrix.shape) < 2:
        return ModelResult(model=None, model_type="fallback", trained=False, hyperparameters={})

    thread_text, thread_categories, thread_numeric = _encode_threads(threads, interactions, interaction_matrix)
    user_text, user_categories, user_numeric = _encode_users(interactions, interaction_matrix, thread_text, thread_categories)
    n_components = max(1, min(48, min(interaction_matrix.matrix.shape) - 1))
    svd = TruncatedSVD(n_components=n_components, random_state=random_state)
    user_factors = svd.fit_transform(interaction_matrix.matrix.astype(np.float32))
    latent_scores = user_factors @ svd.components_
    hyperparameters: dict[str, object] = {
        "n_components": n_components,
        "text_features": TEXT_FEATURES,
        "model_family": "factorization_machine_lightfm_style",
        "feature_mix": "latent_interactions + user/thread text/category/numeric affinity",
    }
    model = FeatureAwareFactorizationRecommender(
        latent_scores=latent_scores.astype(np.float32),
        user_to_index=interaction_matrix.user_to_index,
        thread_to_index=interaction_matrix.thread_to_index,
        index_to_thread=interaction_matrix.index_to_thread,
        user_text=user_text,
        user_categories=user_categories,
        user_numeric=user_numeric,
        thread_text=thread_text,
        thread_categories=thread_categories,
        thread_numeric=thread_numeric,
        hyperparameters=hyperparameters,
    )
    return ModelResult(model=model, model_type="factorization_machine_svd", trained=True, hyperparameters=hyperparameters)


def train_two_tower_model(
    threads: pl.DataFrame,
    interactions: pl.DataFrame,
    interaction_matrix: InteractionMatrix,
    random_state: int = 42,
) -> ModelResult:
    if interactions.is_empty() or interaction_matrix.matrix.nnz == 0 or not interaction_matrix.user_to_index or not interaction_matrix.thread_to_index:
        return ModelResult(model=None, model_type="fallback", trained=False, hyperparameters={})

    thread_text, thread_categories, thread_numeric = _encode_threads(threads, interactions, interaction_matrix)
    user_text, user_categories, user_numeric = _encode_users(interactions, interaction_matrix, thread_text, thread_categories)
    user_features = sparse.hstack(
        [user_text, user_categories, sparse.csr_matrix(user_numeric[:, : thread_numeric.shape[1]])],
        format="csr",
        dtype=np.float32,
    )
    thread_features = sparse.hstack([thread_text, thread_categories, sparse.csr_matrix(thread_numeric)], format="csr", dtype=np.float32)
    combined = sparse.vstack([user_features, thread_features], format="csr", dtype=np.float32)
    n_components = max(1, min(32, min(combined.shape) - 1))
    svd = TruncatedSVD(n_components=n_components, random_state=random_state)
    projected = svd.fit_transform(combined)
    user_vectors = _normalize_rows(projected[: user_features.shape[0]])
    thread_vectors = _normalize_rows(projected[user_features.shape[0] :])
    collaborative = interaction_matrix.matrix.astype(np.float32)
    if collaborative.nnz:
        user_vectors = _normalize_rows(user_vectors + 0.15 * _dense_user_collaborative_projection(collaborative, thread_vectors))
    hyperparameters: dict[str, object] = {
        "n_components": n_components,
        "text_features": TEXT_FEATURES,
        "score": "dot(user_tower(user_history), thread_tower(title+categories+content+features))",
        "model_family": "two_tower_dot_product",
    }
    model = TwoTowerDotRecommender(
        user_vectors=user_vectors.astype(np.float32),
        thread_vectors=thread_vectors.astype(np.float32),
        user_to_index=interaction_matrix.user_to_index,
        thread_to_index=interaction_matrix.thread_to_index,
        index_to_thread=interaction_matrix.index_to_thread,
        hyperparameters=hyperparameters,
    )
    return ModelResult(model=model, model_type="two_tower_dot", trained=True, hyperparameters=hyperparameters)


def _train_pair_feature_classifier(
    threads: pl.DataFrame,
    interactions: pl.DataFrame,
    interaction_matrix: InteractionMatrix,
    random_state: int,
    model_type: str,
    loss: str,
    alpha: float,
    max_iter: int,
    ranking_weights: bool,
) -> ModelResult:
    if interactions.is_empty() or interaction_matrix.matrix.nnz == 0 or not interaction_matrix.user_to_index or not interaction_matrix.thread_to_index:
        return ModelResult(model=None, model_type="fallback", trained=False, hyperparameters={})

    thread_text, thread_categories, thread_numeric = _encode_threads(threads, interactions, interaction_matrix)
    user_text, user_categories, user_numeric = _encode_users(interactions, interaction_matrix, thread_text, thread_categories)
    pair_user_indices, pair_thread_indices, labels, sample_weight = _training_pairs(interactions, interaction_matrix, random_state)

    if len(set(labels.tolist())) < 2:
        return ModelResult(model=None, model_type="fallback", trained=False, hyperparameters={})

    x_train = _pair_features(
        pair_user_indices,
        pair_thread_indices,
        user_text,
        user_categories,
        user_numeric,
        thread_text,
        thread_categories,
        thread_numeric,
    )
    hyperparameters: dict[str, object] = {
        "loss": loss,
        "alpha": alpha,
        "max_iter": max_iter,
        "text_features": TEXT_FEATURES,
        "max_negatives_per_user": MAX_NEGATIVES_PER_USER,
        "ranking_weights": ranking_weights,
    }
    if ranking_weights:
        sample_weight = _rank_weighted_samples(sample_weight, labels)
    classifier = SGDClassifier(
        loss=str(hyperparameters["loss"]),
        alpha=float(hyperparameters["alpha"]),
        max_iter=int(hyperparameters["max_iter"]),
        tol=1e-3,
        class_weight="balanced",
        random_state=random_state,
    )
    classifier.fit(x_train, labels, sample_weight=sample_weight)
    model = EntityFeatureRecommender(
        classifier=classifier,
        user_to_index=interaction_matrix.user_to_index,
        thread_to_index=interaction_matrix.thread_to_index,
        index_to_thread=interaction_matrix.index_to_thread,
        user_text=user_text,
        user_categories=user_categories,
        user_numeric=user_numeric,
        thread_text=thread_text,
        thread_categories=thread_categories,
        thread_numeric=thread_numeric,
        hyperparameters=hyperparameters,
    )
    return ModelResult(model=model, model_type=model_type, trained=True, hyperparameters=hyperparameters)


def _encode_threads(threads: pl.DataFrame, interactions: pl.DataFrame, matrix: InteractionMatrix) -> tuple[sparse.csr_matrix, sparse.csr_matrix, np.ndarray]:
    indexed_threads = _threads_by_matrix_order(threads, matrix)
    _thread_ids, documents, _hashes = thread_documents(indexed_threads)
    vectorizer = HashingVectorizer(n_features=TEXT_FEATURES, alternate_sign=False, norm="l2")
    text = vectorizer.transform(documents).astype(np.float32)

    category_names = sorted(
        {
            str(category)
            for row in indexed_threads.select("categories").iter_rows(named=True)
            for category in (row.get("categories") or [])
        }
    )
    category_to_index = {category: idx for idx, category in enumerate(category_names)}
    row_indices: list[int] = []
    col_indices: list[int] = []
    for row_idx, row in enumerate(indexed_threads.select("categories").iter_rows(named=True)):
        for category in row.get("categories") or []:
            if str(category) in category_to_index:
                row_indices.append(row_idx)
                col_indices.append(category_to_index[str(category)])
    categories = sparse.csr_matrix(
        (np.ones(len(row_indices), dtype=np.float32), (row_indices, col_indices)),
        shape=(indexed_threads.height, len(category_names)),
        dtype=np.float32,
    )

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    popularity_by_thread = (
        dict(interactions.group_by("thread_id").agg(pl.sum("score").alias("score")).iter_rows())
        if interactions.height
        else {}
    )
    max_popularity = max((float(value) for value in popularity_by_thread.values()), default=1.0)
    popularity = []
    freshness = []
    author_hash = []
    for row in indexed_threads.iter_rows(named=True):
        created_at = row.get("created_at")
        if isinstance(created_at, datetime):
            created_naive = created_at.replace(tzinfo=None) if created_at.tzinfo else created_at
            age_days = max((now - created_naive).days, 0)
        else:
            age_days = 365
        freshness.append(math.exp(-age_days / 45.0))
        popularity.append(math.log1p(float(popularity_by_thread.get(row["thread_id"], 0.0))) / math.log1p(max(max_popularity, 1.0)))
        author_hash.append(_stable_unit_hash(str(row.get("author_user_id") or "")))
    numeric = np.column_stack([freshness, popularity, author_hash]).astype(np.float32)
    return text, categories, numeric


def _encode_users(
    interactions: pl.DataFrame,
    matrix: InteractionMatrix,
    thread_text: sparse.csr_matrix,
    thread_categories: sparse.csr_matrix,
) -> tuple[sparse.csr_matrix, sparse.csr_matrix, np.ndarray]:
    users_count = len(matrix.user_to_index)
    text_rows = sparse.lil_matrix((users_count, thread_text.shape[1]), dtype=np.float32)
    category_rows = sparse.lil_matrix((users_count, thread_categories.shape[1]), dtype=np.float32)
    numeric = np.zeros((users_count, 6), dtype=np.float32)

    max_events = float(interactions.get_column("events_count").max()) if interactions.height else 1.0
    max_score = float(interactions.get_column("score").max()) if interactions.height else 1.0
    for user_id, group in interactions.group_by("user_id"):
        user_key = user_id[0] if isinstance(user_id, tuple) else user_id
        user_idx = matrix.user_to_index.get(str(user_key))
        if user_idx is None:
            continue
        thread_indices = [matrix.thread_to_index[thread_id] for thread_id in group.get_column("thread_id").to_list() if thread_id in matrix.thread_to_index]
        if not thread_indices:
            continue
        weights = group.filter(pl.col("thread_id").is_in([matrix.index_to_thread[idx] for idx in thread_indices])).get_column("score").cast(pl.Float32).to_numpy()
        weights = np.maximum(weights, 0.01)
        text_rows[user_idx] = _weighted_average(thread_text[thread_indices], weights)
        if thread_categories.shape[1]:
            category_rows[user_idx] = _weighted_average(thread_categories[thread_indices], weights)
        numeric[user_idx] = np.asarray(
            [
                math.log1p(float(group.get_column("events_count").sum())) / math.log1p(max(max_events, 1.0)),
                math.log1p(float(group.get_column("score").sum())) / math.log1p(max(max_score, 1.0)),
                float(group.get_column("thread_id").n_unique()) / max(len(matrix.thread_to_index), 1),
                _normalized_sum(group, "thread_viewed_count"),
                _normalized_sum(group, "like_count"),
                _normalized_sum(group, "recommendation_clicked_count"),
            ],
            dtype=np.float32,
        )
    return text_rows.tocsr(), category_rows.tocsr(), numeric


def _training_pairs(
    interactions: pl.DataFrame,
    matrix: InteractionMatrix,
    random_state: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    rng = random.Random(random_state)
    all_thread_indices = set(range(len(matrix.thread_to_index)))
    positives_by_user: dict[int, list[tuple[int, float]]] = {}
    for row in interactions.select("user_id", "thread_id", "score").iter_rows(named=True):
        user_idx = matrix.user_to_index.get(row["user_id"])
        thread_idx = matrix.thread_to_index.get(row["thread_id"])
        if user_idx is None or thread_idx is None:
            continue
        positives_by_user.setdefault(user_idx, []).append((thread_idx, max(float(row["score"]), 0.01)))

    user_indices: list[int] = []
    thread_indices: list[int] = []
    labels: list[int] = []
    sample_weight: list[float] = []
    for user_idx, positives in positives_by_user.items():
        positive_thread_indices = {thread_idx for thread_idx, _score in positives}
        for thread_idx, score in positives:
            user_indices.append(user_idx)
            thread_indices.append(thread_idx)
            labels.append(1)
            sample_weight.append(math.log1p(score))

        negative_pool = list(all_thread_indices - positive_thread_indices)
        rng.shuffle(negative_pool)
        negative_count = min(len(negative_pool), max(len(positives), 1), MAX_NEGATIVES_PER_USER)
        for thread_idx in negative_pool[:negative_count]:
            user_indices.append(user_idx)
            thread_indices.append(thread_idx)
            labels.append(0)
            sample_weight.append(1.0)

    return (
        np.asarray(user_indices, dtype=np.int64),
        np.asarray(thread_indices, dtype=np.int64),
        np.asarray(labels, dtype=np.int64),
        np.asarray(sample_weight, dtype=np.float32),
    )


def _pair_features(
    user_indices: np.ndarray,
    thread_indices: np.ndarray,
    user_text: sparse.csr_matrix,
    user_categories: sparse.csr_matrix,
    user_numeric: np.ndarray,
    thread_text: sparse.csr_matrix,
    thread_categories: sparse.csr_matrix,
    thread_numeric: np.ndarray,
) -> sparse.csr_matrix:
    user_text_rows = user_text[user_indices]
    thread_text_rows = thread_text[thread_indices]
    user_category_rows = user_categories[user_indices]
    thread_category_rows = thread_categories[thread_indices]
    numeric = sparse.csr_matrix(np.hstack([user_numeric[user_indices], thread_numeric[thread_indices]]).astype(np.float32))
    return sparse.hstack(
        [
            user_text_rows,
            thread_text_rows,
            user_text_rows.multiply(thread_text_rows),
            user_category_rows,
            thread_category_rows,
            user_category_rows.multiply(thread_category_rows),
            numeric,
        ],
        format="csr",
        dtype=np.float32,
    )


def _pair_features_for_user(
    user_index: int,
    user_text: sparse.csr_matrix,
    user_categories: sparse.csr_matrix,
    user_numeric: np.ndarray,
    thread_text: sparse.csr_matrix,
    thread_categories: sparse.csr_matrix,
    thread_numeric: np.ndarray,
) -> sparse.csr_matrix:
    thread_indices = np.arange(thread_text.shape[0], dtype=np.int64)
    user_indices = np.full(thread_text.shape[0], user_index, dtype=np.int64)
    return _pair_features(
        user_indices,
        thread_indices,
        user_text,
        user_categories,
        user_numeric,
        thread_text,
        thread_categories,
        thread_numeric,
    )


def _threads_by_matrix_order(threads: pl.DataFrame, matrix: InteractionMatrix) -> pl.DataFrame:
    if threads.is_empty():
        return threads
    order = pl.DataFrame(
        {
            "thread_id": [matrix.index_to_thread[idx] for idx in range(len(matrix.index_to_thread))],
            "__order": list(range(len(matrix.index_to_thread))),
        }
    )
    return order.join(threads, on="thread_id", how="left").sort("__order").drop("__order")


def _weighted_average(rows: sparse.csr_matrix, weights: np.ndarray) -> sparse.csr_matrix:
    if rows.shape[0] == 0:
        return sparse.csr_matrix((1, rows.shape[1]), dtype=np.float32)
    normalized = weights / max(float(weights.sum()), 1e-6)
    return sparse.csr_matrix(normalized.reshape(1, -1) @ rows)


def _stable_unit_hash(value: str) -> float:
    digest = sha256(value.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF


def _normalized_sum(frame: pl.DataFrame, column: str) -> float:
    if column not in frame.columns:
        return 0.0
    values = frame.get_column(column)
    max_value = max(float(values.max() or 0.0), 1.0)
    return math.log1p(float(values.sum())) / math.log1p(max_value)


def _rank_weighted_samples(sample_weight: np.ndarray, labels: np.ndarray) -> np.ndarray:
    weights = sample_weight.astype(np.float32, copy=True)
    positive_mask = labels == 1
    if positive_mask.any():
        weights[positive_mask] = 1.0 + _normalize_vector(weights[positive_mask]) * 4.0
    return weights


def _normalize_vector(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float32)
    if values.size == 0:
        return values
    finite = np.isfinite(values)
    if not finite.any():
        return np.zeros_like(values, dtype=np.float32)
    clean = np.where(finite, values, 0.0)
    minimum = float(clean.min())
    maximum = float(clean.max())
    if math.isclose(minimum, maximum):
        return np.zeros_like(clean, dtype=np.float32)
    return ((clean - minimum) / (maximum - minimum)).astype(np.float32)


def _normalize_rows(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float32)
    norms = np.linalg.norm(values, axis=1, keepdims=True)
    return values / np.maximum(norms, 1e-6)


def _dense_user_collaborative_projection(matrix: sparse.csr_matrix, thread_vectors: np.ndarray) -> np.ndarray:
    projected = matrix @ thread_vectors
    counts = np.asarray((matrix > 0).sum(axis=1)).reshape(-1, 1)
    return projected / np.maximum(counts, 1.0)
