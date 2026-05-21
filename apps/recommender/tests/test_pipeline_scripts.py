from dataclasses import replace
from datetime import date, datetime, timezone
import json

import polars as pl

import generate_recommendations
import train_model
from recommender.config import RecommenderConfig
from recommender.data import BehaviorData, BusinessData, empty_frame, EMPTY_COMMENTS, EMPTY_LIKES, EMPTY_POSTS


class FakeClickHouse:
    def __init__(self):
        self.inserts = []

    def insert(self, table, rows, column_names):
        self.inserts.append({"table": table, "rows": rows, "column_names": column_names})


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


def _business(now: datetime) -> BusinessData:
    return BusinessData(
        users=pl.DataFrame(
            {
                "user_id": ["user-backend", "user-frontend"],
                "username": ["backend-user", "frontend-user"],
                "created_at": [now, now],
            }
        ),
        threads=pl.DataFrame(
            {
                "thread_id": ["go-seen", "go-new", "react-seen", "react-new"],
                "title": ["Go database tuning", "Go profiling", "React hooks", "React suspense"],
                "categories": [["go", "backend"], ["go", "backend"], ["react", "frontend"], ["react", "frontend"]],
                "content": [
                    "postgres connection pooling query plan",
                    "go profiler cpu memory database",
                    "react hook state rendering",
                    "react suspense cache boundary",
                ],
                "author_user_id": ["author-1", "author-2", "author-3", "author-4"],
                "created_at": [now, now, now, now],
                "updated_at": [now, now, now, now],
            }
        ),
        posts=empty_frame(EMPTY_POSTS),
        comments=empty_frame(EMPTY_COMMENTS),
        likes=empty_frame(EMPTY_LIKES),
    )


def _behavior(now: datetime) -> BehaviorData:
    return BehaviorData(
        events=pl.DataFrame(
            {
                "user_id": ["user-backend", "user-frontend"],
                "event_type": ["thread_viewed", "thread_viewed"],
                "entity_type": ["thread", "thread"],
                "entity_id": ["go-seen", "react-seen"],
                "thread_id": ["go-seen", "react-seen"],
                "metadata": ["{}", "{}"],
                "created_at": [now, now],
            }
        ),
        user_thread_daily=pl.DataFrame(
            {
                "event_date": [date(2026, 5, 19), date(2026, 5, 19)],
                "user_id": ["user-backend", "user-frontend"],
                "thread_id": ["go-seen", "react-seen"],
                "event_type": ["thread_viewed", "thread_viewed"],
                "events_count": [4.0, 4.0],
            }
        ),
        recommendation_daily=pl.DataFrame(
            {
                "event_date": [date(2026, 5, 19)],
                "user_id": ["user-backend"],
                "thread_id": ["go-new"],
                "model_version": ["previous-model"],
                "impressions": [10.0],
                "clicks": [2.0],
                "ctr": [0.2],
                "avg_position": [1.5],
            }
        ),
    )


def test_train_and_generate_scripts_run_on_synthetic_timezone_aware_data(tmp_path, monkeypatch):
    now = datetime(2026, 5, 19, 12, tzinfo=timezone.utc)
    config = _config(tmp_path)
    business = _business(now)
    behavior = _behavior(now)
    clickhouse = FakeClickHouse()

    monkeypatch.setattr(train_model, "load_business_data", lambda _postgres: business)
    monkeypatch.setattr(train_model, "load_behavior_data", lambda _clickhouse, days: behavior)

    metrics = train_model.run_training(config, object(), clickhouse, "train-run", events_days=30, metrics_k=2)

    assert (tmp_path / "model.joblib").exists()
    assert not (tmp_path / "champion_report.md").exists()
    assert metrics["recommendation_ctr"] == 0.2
    assert metrics["model_type"] == "catboost_ranker"
    assert metrics["model_trained"] is True
    assert metrics["catboost_ranker_score"] >= 0.0
    assert metrics["training_rows"] > 0
    assert "ml_candidates" not in metrics
    assert "champion_model_type" not in metrics
    assert any(insert["table"] == "recommendation_runs" for insert in clickhouse.inserts)
    metadata = json.loads((tmp_path / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["model_type"] == "catboost_ranker"
    assert metadata["params"]["model_type"] == "catboost_ranker"
    assert metadata["feature_schema_version"] == "catboost_ranker_features_v1"

    generation_clickhouse = FakeClickHouse()
    monkeypatch.setattr(generate_recommendations, "load_business_data", lambda _postgres: business)
    monkeypatch.setattr(generate_recommendations, "load_behavior_data", lambda _clickhouse, days: behavior)

    generation_metrics = generate_recommendations.run_generation(
        replace(config, top_n=1),
        object(),
        generation_clickhouse,
        "generate-run",
        events_days=30,
    )

    assert generation_metrics["history_recommendations"] == 2.0
    assert generation_metrics["model_type"] == "catboost_ranker"
    assert any(insert["table"] == "recommendation_history" for insert in generation_clickhouse.inserts)
