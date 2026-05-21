from datetime import datetime, timezone

import polars as pl
import numpy as np

from recommender.baselines import latest_active, thread_affinity_recent
from recommender.matrix import InteractionMatrix
from recommender.matrix import build_interaction_matrix
from recommender.modeling import ModelResult
from recommender.recommendations import generate_for_users


def test_latest_active_handles_timezone_aware_and_naive_datetimes():
    aware = datetime(2026, 5, 19, 12, tzinfo=timezone.utc)
    naive = datetime(2026, 5, 18, 12)
    threads = pl.DataFrame(
        {
            "thread_id": ["older", "newer"],
            "title": ["Old", "New"],
            "categories": [["go"], ["go"]],
            "author_user_id": ["author-1", "author-2"],
            "created_at": [naive, aware],
            "updated_at": [naive, aware],
        }
    )
    interactions = pl.DataFrame(
        {
            "user_id": ["user-1"],
            "thread_id": ["older"],
            "score": [1.0],
            "last_event_at": [aware],
            "events_count": [1.0],
        }
    )

    ranked = latest_active(threads, interactions, limit=2)

    assert [thread_id for thread_id, _score in ranked] == ["older", "newer"]


def test_sparse_user_skips_model_and_uses_affinity_fallback():
    now = datetime(2026, 5, 19, tzinfo=timezone.utc)
    threads = pl.DataFrame(
        {
            "thread_id": ["go-seen", "go-new", "react-new"],
            "title": ["Go channels", "Go profiling", "React hooks"],
            "categories": [["go"], ["go"], ["react"]],
            "author_user_id": ["author-1", "author-2", "author-3"],
            "created_at": [now, now, now],
            "updated_at": [now, now, now],
        }
    )
    interactions = pl.DataFrame(
        {
            "user_id": ["user-1"],
            "thread_id": ["go-seen"],
            "score": [3.0],
            "last_event_at": [now],
            "events_count": [1.0],
        }
    )
    matrix = build_interaction_matrix(interactions)

    recommendations = generate_for_users(
        ["user-1"],
        threads,
        interactions,
        matrix,
        ModelResult(model=object(), model_type="test", trained=True),
        top_n=2,
        candidate_pool_size=10,
        min_model_interactions=20,
    )

    assert recommendations["user-1"][0][0] == "go-new"
    assert recommendations["user-1"][0][2] == "fallback_thread_affinity_recent"


def test_normal_user_gets_model_only_without_baseline_mixing():
    now = datetime(2026, 5, 19, tzinfo=timezone.utc)
    threads = pl.DataFrame(
        {
            "thread_id": ["go-seen", "go-new", "react-new"],
            "title": ["Go channels", "Go profiling", "React hooks"],
            "categories": [["go"], ["go"], ["react"]],
            "author_user_id": ["author-1", "author-2", "author-3"],
            "created_at": [now, now, now],
            "updated_at": [now, now, now],
        }
    )
    interactions = pl.DataFrame(
        {
            "user_id": ["user-1", "user-2"],
            "thread_id": ["go-seen", "go-new"],
            "score": [3.0, 2.0],
            "last_event_at": [now, now],
            "events_count": [25.0, 3.0],
        }
    )
    matrix = InteractionMatrix(
        matrix=build_interaction_matrix(interactions).matrix,
        user_to_index={"user-1": 0, "user-2": 1},
        thread_to_index={"go-seen": 0, "go-new": 1},
        index_to_user={0: "user-1", 1: "user-2"},
        index_to_thread={0: "go-seen", 1: "go-new"},
    )

    class FakeModel:
        def recommend(self, user_index, user_items, N, filter_already_liked_items=True):
            return np.array([1]), np.array([0.9])

    recommendations = generate_for_users(
        ["user-1"],
        threads,
        interactions,
        matrix,
        ModelResult(model=FakeModel(), model_type="entity_feature_sgd", trained=True),
        top_n=2,
        candidate_pool_size=10,
        min_model_interactions=20,
    )

    assert recommendations["user-1"] == [("go-new", 0.9, "model")]


def test_recommendations_never_emit_threads_outside_current_catalog():
    now = datetime(2026, 5, 19, tzinfo=timezone.utc)
    threads = pl.DataFrame(
        {
            "thread_id": ["go-seen", "go-new"],
            "title": ["Go channels", "Go profiling"],
            "categories": [["go"], ["go"]],
            "author_user_id": ["author-1", "author-2"],
            "created_at": [now, now],
            "updated_at": [now, now],
        }
    )
    interactions = pl.DataFrame(
        {
            "user_id": ["user-1", "user-2", "user-3"],
            "thread_id": ["go-seen", "go-new", "ghost-thread"],
            "score": [3.0, 2.0, 4.0],
            "last_event_at": [now, now, now],
            "events_count": [25.0, 3.0, 50.0],
        }
    )
    matrix = InteractionMatrix(
        matrix=build_interaction_matrix(interactions).matrix,
        user_to_index={"user-1": 0, "user-2": 1, "user-3": 2},
        thread_to_index={"ghost-thread": 0, "go-new": 1, "go-seen": 2},
        index_to_user={0: "user-1", 1: "user-2", 2: "user-3"},
        index_to_thread={0: "ghost-thread", 1: "go-new", 2: "go-seen"},
    )

    class FakeModel:
        def recommend(self, user_index, user_items, N, filter_already_liked_items=True):
            return np.array([0, 1]), np.array([0.99, 0.8])

    recommendations = generate_for_users(
        ["user-1"],
        threads,
        interactions,
        matrix,
        ModelResult(model=FakeModel(), model_type="entity_feature_sgd", trained=True),
        top_n=2,
        candidate_pool_size=10,
        min_model_interactions=1,
    )

    assert recommendations["user-1"] == [("go-new", 0.8, "model")]


def test_recommendation_impressions_do_not_exclude_unopened_threads():
    now = datetime(2026, 5, 19, tzinfo=timezone.utc)
    threads = pl.DataFrame(
        {
            "thread_id": ["impressed", "other"],
            "title": ["Go profiling", "React hooks"],
            "categories": [["go"], ["react"]],
            "author_user_id": ["author-1", "author-2"],
            "created_at": [now, now],
            "updated_at": [now, now],
        }
    )
    interactions = pl.DataFrame(
        {
            "user_id": ["user-1"],
            "thread_id": ["impressed"],
            "score": [0.1],
            "last_event_at": [now],
            "events_count": [2.0],
            "thread_viewed_count": [0.0],
            "like_count": [0.0],
            "recommendation_clicked_count": [0.0],
        }
    )
    matrix = build_interaction_matrix(interactions)

    recommendations = generate_for_users(
        ["user-1"],
        threads,
        interactions,
        matrix,
        ModelResult(model=None, model_type="test", trained=False),
        top_n=2,
        candidate_pool_size=10,
        min_model_interactions=20,
    )

    assert recommendations["user-1"][0][0] == "impressed"
    assert recommendations["user-1"][0][2].startswith("fallback_")


def test_thread_affinity_uses_title_categories_and_author_signals():
    now = datetime(2026, 5, 19)
    threads = pl.DataFrame(
        {
            "thread_id": ["seen", "same-author", "same-title", "other"],
            "title": ["PostgreSQL indexes", "Linux shell", "PostgreSQL tuning", "CSS grid"],
            "categories": [["db"], ["ops"], ["db"], ["frontend"]],
            "author_user_id": ["author-a", "author-a", "author-b", "author-c"],
            "created_at": [now, now, now, now],
            "updated_at": [now, now, now, now],
        }
    )
    interactions = pl.DataFrame(
        {
            "user_id": ["user-1"],
            "thread_id": ["seen"],
            "score": [1.0],
            "last_event_at": [now],
            "events_count": [1.0],
        }
    )

    ranked = thread_affinity_recent("user-1", threads, interactions, limit=4)
    ranked_ids = [thread_id for thread_id, _score in ranked]

    assert ranked_ids.index("same-author") < ranked_ids.index("other")
    assert ranked_ids.index("same-title") < ranked_ids.index("other")
