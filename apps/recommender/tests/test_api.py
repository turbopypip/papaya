from dataclasses import replace
from datetime import date, datetime, timezone

import polars as pl

from recommender import api
from recommender.catboost_ranker import CatBoostRankerArtifact, DEFAULT_FEATURE_SCHEMA
from recommender.config import RecommenderConfig
from recommender.data import (
    BehaviorData,
    BusinessData,
    EMPTY_COMMENTS,
    EMPTY_EVENTS,
    EMPTY_LIKES,
    EMPTY_POSTS,
    EMPTY_RECOMMENDATION_DAILY,
    EMPTY_THREADS,
    EMPTY_USER_THREAD_DAILY,
    EMPTY_USERS,
    empty_frame,
)


def _config(tmp_path) -> RecommenderConfig:
    return RecommenderConfig(
        postgres_dsn="postgresql+psycopg://example",
        clickhouse_host="localhost",
        clickhouse_port=8123,
        clickhouse_database="papaya_analytics",
        clickhouse_user="papaya",
        clickhouse_password="secret",
        artifacts_dir=tmp_path,
        model_version="test-model",
        model_type="catboost_ranker",
        top_n=2,
        candidate_pool_size=10,
        half_life_days=21.0,
        min_model_interactions=1,
        random_state=42,
        content_enabled=True,
        content_embedding_model="sentence-transformers/all-MiniLM-L6-v2",
        content_max_generation_seconds=120.0,
    )


def _artifact(model_version: str = "artifact-v1") -> api.LoadedArtifact:
    return api.LoadedArtifact(
        model_artifact=CatBoostRankerArtifact(
            model=None,
            feature_schema=DEFAULT_FEATURE_SCHEMA,
            trained=False,
            hyperparameters={},
        ),
        metadata={"model_version": model_version, "model_type": "catboost_ranker", "params": {}},
    )


class FakeCatBoostModel:
    def predict(self, pool):
        return [float(pool.num_row() - index) for index in range(pool.num_row())]


def _trained_artifact(model_version: str = "artifact-v1") -> api.LoadedArtifact:
    artifact = _artifact(model_version)
    artifact.model_artifact.model = FakeCatBoostModel()
    artifact.model_artifact.trained = True
    return artifact


def _empty_business() -> BusinessData:
    return BusinessData(
        users=empty_frame(EMPTY_USERS),
        threads=empty_frame(EMPTY_THREADS),
        posts=empty_frame(EMPTY_POSTS),
        comments=empty_frame(EMPTY_COMMENTS),
        likes=empty_frame(EMPTY_LIKES),
    )


def _business_with_thread() -> BusinessData:
    now = datetime(2026, 5, 21, 12, tzinfo=timezone.utc)
    return BusinessData(
        users=empty_frame(EMPTY_USERS),
        threads=pl.DataFrame(
            {
                "thread_id": ["backend-thread"],
                "title": ["PostgreSQL connection pooling"],
                "categories": [["backend", "postgresql"]],
                "content": ["How to tune backend connection pools"],
                "author_user_id": ["author-user"],
                "created_at": [now],
                "updated_at": [now],
            }
        ),
        posts=empty_frame(EMPTY_POSTS),
        comments=empty_frame(EMPTY_COMMENTS),
        likes=empty_frame(EMPTY_LIKES),
    )


def _business_with_new_thread() -> BusinessData:
    now = datetime(2026, 5, 21, 12, tzinfo=timezone.utc)
    return BusinessData(
        users=pl.DataFrame(
            {
                "user_id": ["active-user"],
                "username": ["active"],
                "created_at": [now],
            }
        ),
        threads=pl.DataFrame(
            {
                "thread_id": ["seen-thread", "new-thread"],
                "title": ["PostgreSQL connection pooling", "PostgreSQL index tuning"],
                "categories": [["backend", "postgresql"], ["backend", "postgresql"]],
                "content": ["How to tune backend connection pools", "Btree index and query plan tuning"],
                "author_user_id": ["author-user", "other-author"],
                "created_at": [now, now],
                "updated_at": [now, now],
            }
        ),
        posts=empty_frame(EMPTY_POSTS),
        comments=empty_frame(EMPTY_COMMENTS),
        likes=empty_frame(EMPTY_LIKES),
    )


def _empty_behavior() -> BehaviorData:
    return BehaviorData(
        events=empty_frame(EMPTY_EVENTS),
        user_thread_daily=empty_frame(EMPTY_USER_THREAD_DAILY),
        recommendation_daily=empty_frame(EMPTY_RECOMMENDATION_DAILY),
    )


def _active_behavior() -> BehaviorData:
    now = datetime(2026, 5, 21, 12, tzinfo=timezone.utc)
    return BehaviorData(
        events=empty_frame(EMPTY_EVENTS),
        user_thread_daily=pl.DataFrame(
            {
                "event_date": [date(2026, 5, 21)],
                "user_id": ["active-user"],
                "thread_id": ["seen-thread"],
                "event_type": ["thread_viewed"],
                "events_count": [3.0],
            }
        ),
        recommendation_daily=empty_frame(EMPTY_RECOMMENDATION_DAILY),
    )


def test_create_app_loads_artifact_and_logs_state(tmp_path, monkeypatch, caplog):
    monkeypatch.setattr(api, "_load_production_artifact", lambda _artifacts_dir: _artifact())
    monkeypatch.setattr(api, "load_content_index", lambda _artifacts_dir: object())

    with caplog.at_level("INFO", logger="recommender.api"):
        app = api.create_app(_config(tmp_path))

    assert app.state.model_loaded is True
    assert app.state.model_version == "artifact-v1"
    assert app.state.content_index_loaded is True
    assert "model_loaded=True" in caplog.text
    assert "model_version=artifact-v1" in caplog.text


def test_recommendations_empty_catalog_returns_no_recommendations(tmp_path, monkeypatch):
    config = replace(_config(tmp_path), content_enabled=False)
    monkeypatch.setattr(api, "create_postgres_engine", lambda _config: object())
    monkeypatch.setattr(api, "create_clickhouse_client", lambda _config: object())
    monkeypatch.setattr(api, "load_business_data", lambda _postgres: _empty_business())
    monkeypatch.setattr(api, "load_behavior_data", lambda _clickhouse, days: _empty_behavior())

    response = api.generate_thread_recommendations(
        config,
        api.ThreadRecommendationRequest(user_id="new-user", limit=5),
        artifact=_artifact("artifact-v1"),
    )

    assert response.status == api.STATUS_NO_RECOMMENDATIONS
    assert response.recommendations == []
    assert response.model_version == "artifact-v1"


def test_recommendations_use_explicit_fallback_only_when_catalog_has_threads(tmp_path, monkeypatch):
    config = replace(_config(tmp_path), content_enabled=False, min_model_interactions=100)
    monkeypatch.setattr(api, "create_postgres_engine", lambda _config: object())
    monkeypatch.setattr(api, "create_clickhouse_client", lambda _config: object())
    monkeypatch.setattr(api, "load_business_data", lambda _postgres: _business_with_thread())
    monkeypatch.setattr(api, "load_behavior_data", lambda _clickhouse, days: _empty_behavior())

    response = api.generate_thread_recommendations(
        config,
        api.ThreadRecommendationRequest(user_id="new-user", limit=5),
        artifact=_artifact("artifact-v1"),
    )

    assert response.status == api.STATUS_READY
    assert len(response.recommendations) == 1
    assert response.recommendations[0].thread_id == "backend-thread"
    assert response.recommendations[0].recommendation_source.startswith("fallback_")


def test_active_new_user_gets_model_ranked_new_thread_without_matrix_membership(tmp_path, monkeypatch):
    config = replace(_config(tmp_path), content_enabled=False, min_model_interactions=1)
    monkeypatch.setattr(api, "create_postgres_engine", lambda _config: object())
    monkeypatch.setattr(api, "create_clickhouse_client", lambda _config: object())
    monkeypatch.setattr(api, "load_business_data", lambda _postgres: _business_with_new_thread())
    monkeypatch.setattr(api, "load_behavior_data", lambda _clickhouse, days: _active_behavior())

    response = api.generate_thread_recommendations(
        config,
        api.ThreadRecommendationRequest(user_id="active-user", limit=5),
        artifact=_trained_artifact("artifact-v1"),
    )

    assert response.status == api.STATUS_READY
    assert [item.thread_id for item in response.recommendations] == ["new-thread"]
    assert response.recommendations[0].recommendation_source == "model"
    assert response.recommendations[0].metadata["model_type"] == "catboost_ranker"


def test_recommendations_missing_artifact_is_model_not_ready(tmp_path, monkeypatch):
    config = _config(tmp_path)
    monkeypatch.setattr(api, "_load_production_artifact", lambda _artifacts_dir: None)

    response = api.generate_thread_recommendations(
        config,
        api.ThreadRecommendationRequest(user_id="new-user", limit=5),
    )

    assert response.status == api.STATUS_MODEL_NOT_READY
    assert response.recommendations == []
    assert response.model_version is None
