from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv


DEFAULT_EVENT_WEIGHTS = {
    "thread_viewed": 1.0,
    "post_created": 4.0,
    "comment_created": 3.0,
    "post_liked": 2.5,
    "comment_liked": 2.0,
    "thread_created": 1.5,
    "recommendation_impression": 0.05,
    "recommendation_clicked": 3.0,
}


@dataclass(frozen=True)
class RecommenderConfig:
    postgres_dsn: str
    clickhouse_host: str
    clickhouse_port: int
    clickhouse_database: str
    clickhouse_user: str
    clickhouse_password: str
    artifacts_dir: Path
    model_version: str
    model_type: str
    top_n: int
    candidate_pool_size: int
    half_life_days: float
    min_model_interactions: int
    random_state: int
    content_enabled: bool
    content_embedding_model: str
    content_max_generation_seconds: float

    @classmethod
    def from_env(cls, env_file: str | None = None) -> "RecommenderConfig":
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()

        pg_dsn = os.getenv("RECOMMENDER_POSTGRES_DSN")
        if not pg_dsn:
            pg_user = os.getenv("POSTGRES_USER", "papaya")
            pg_password = os.getenv("POSTGRES_PASSWORD", "papaya_password")
            pg_host = os.getenv("POSTGRES_HOST", "localhost")
            pg_port = os.getenv("PG_PORT", "5432")
            pg_db = os.getenv("POSTGRES_DB", "papaya")
            pg_dsn = f"postgresql+psycopg://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_db}"

        return cls(
            postgres_dsn=pg_dsn,
            clickhouse_host=os.getenv("CLICKHOUSE_HTTP_HOST", os.getenv("CLICKHOUSE_HOST", "localhost")),
            clickhouse_port=int(os.getenv("CLICKHOUSE_HTTP_PORT", "8123")),
            clickhouse_database=os.getenv("CLICKHOUSE_DB", "papaya_analytics"),
            clickhouse_user=os.getenv("CLICKHOUSE_USER", "papaya"),
            clickhouse_password=os.getenv("CLICKHOUSE_PASSWORD", "papaya_analytics_password"),
            artifacts_dir=Path(os.getenv("RECOMMENDER_ARTIFACTS_DIR", "apps/recommender/artifacts")),
            model_version=os.getenv("RECOMMENDER_MODEL_VERSION", "entity-feature-v1"),
            model_type=os.getenv("RECOMMENDER_MODEL_TYPE", "winner"),
            top_n=int(os.getenv("RECOMMENDER_TOP_N", "20")),
            candidate_pool_size=int(os.getenv("RECOMMENDER_CANDIDATE_POOL_SIZE", "100")),
            half_life_days=float(os.getenv("RECOMMENDER_HALF_LIFE_DAYS", "21")),
            min_model_interactions=int(os.getenv("RECOMMENDER_MIN_MODEL_INTERACTIONS", "20")),
            random_state=int(os.getenv("RECOMMENDER_RANDOM_STATE", "42")),
            content_enabled=os.getenv("RECOMMENDER_CONTENT_ENABLED", "true").lower() in {"1", "true", "yes", "on"},
            content_embedding_model=os.getenv("RECOMMENDER_CONTENT_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
            content_max_generation_seconds=float(os.getenv("RECOMMENDER_CONTENT_MAX_GENERATION_SECONDS", "120")),
        )
