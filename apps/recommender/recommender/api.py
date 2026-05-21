from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import argparse
import json
import logging
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI
from pydantic import BaseModel, Field

from recommender.artifacts import METADATA_FILENAME, load_artifacts
from recommender.catboost_ranker import CatBoostRankerArtifact, FeatureSchema, MODEL_TYPE, generate_catboost_for_users
from recommender.clients import create_clickhouse_client, create_postgres_engine
from recommender.config import RecommenderConfig
from recommender.content import load_content_index
from recommender.etl import prepare_data
from recommender.loaders import load_behavior_data, load_business_data


STATUS_READY = "ready"
STATUS_MODEL_NOT_READY = "model_not_ready"
STATUS_NO_RECOMMENDATIONS = "no_recommendations"

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")


class ThreadRecommendationRequest(BaseModel):
    user_id: str = Field(min_length=1)
    limit: int = Field(default=10, ge=1, le=50)
    events_days: int = Field(default=180, ge=1, le=730)


class ThreadRecommendationItem(BaseModel):
    thread_id: str
    score: float
    recommendation_source: str
    model_version: str
    run_id: str | None = None
    generation_id: str
    metadata: dict[str, object] = Field(default_factory=dict)


class ThreadRecommendationResponse(BaseModel):
    status: str
    recommendations: list[ThreadRecommendationItem]
    model_version: str | None = None
    run_id: str | None = None
    generation_id: str
    generated_at: str
    metadata: dict[str, object] = Field(default_factory=dict)


@dataclass
class LoadedArtifact:
    model_artifact: CatBoostRankerArtifact
    metadata: dict[str, object]


def create_app(config: RecommenderConfig | None = None) -> FastAPI:
    app = FastAPI(title="Papaya Recommender", version="0.1.0")
    app.state.config = config or RecommenderConfig.from_env()
    _initialize_serving_state(app)

    @app.get("/health")
    def health() -> dict[str, object]:
        return {
            "status": "ok",
            "model_loaded": bool(app.state.model_loaded),
            "model_version": app.state.model_version,
            "content_index_loaded": bool(app.state.content_index_loaded),
        }

    @app.post("/recommendations/threads", response_model=ThreadRecommendationResponse)
    def recommend_threads(payload: ThreadRecommendationRequest) -> ThreadRecommendationResponse:
        return generate_thread_recommendations(
            app.state.config,
            payload,
            artifact=app.state.loaded_artifact,
            content_index=app.state.content_index,
        )

    return app


def generate_thread_recommendations(
    config: RecommenderConfig,
    payload: ThreadRecommendationRequest,
    artifact: LoadedArtifact | None = None,
    content_index=None,
) -> ThreadRecommendationResponse:
    generation_id = str(uuid4())
    generated_at = datetime.now(timezone.utc).isoformat()
    artifact = artifact if artifact is not None else _load_production_artifact(config.artifacts_dir)
    if artifact is None:
        return _empty_response(STATUS_MODEL_NOT_READY, generation_id, generated_at)

    postgres = create_postgres_engine(config)
    clickhouse = create_clickhouse_client(config)
    business = load_business_data(postgres)
    behavior = load_behavior_data(clickhouse, days=payload.events_days)
    prepared = prepare_data(business, behavior, half_life_days=config.half_life_days)

    if content_index is None and config.content_enabled:
        content_index = load_content_index(config.artifacts_dir)
    recommendations = generate_catboost_for_users(
        [payload.user_id],
        business,
        prepared.interactions,
        artifact.model_artifact,
        top_n=payload.limit,
        candidate_pool_size=max(config.candidate_pool_size, payload.limit),
        min_model_interactions=config.min_model_interactions,
    ).get(payload.user_id, [])

    model_version = str(artifact.metadata.get("model_version") or config.model_version)
    params = artifact.metadata.get("params", {}) if isinstance(artifact.metadata.get("params"), dict) else {}
    run_id = str(params.get("run_id") or "") or None
    metadata = {
        "model_type": MODEL_TYPE,
        "feature_schema_version": artifact.model_artifact.feature_schema.version,
    }
    items = [
        ThreadRecommendationItem(
            thread_id=thread_id,
            score=float(score),
            recommendation_source=source,
            model_version=model_version,
            run_id=run_id,
            generation_id=generation_id,
            metadata=metadata,
        )
        for thread_id, score, source in recommendations
    ]
    status = STATUS_READY if items else STATUS_NO_RECOMMENDATIONS
    return ThreadRecommendationResponse(
        status=status,
        recommendations=items,
        model_version=model_version,
        run_id=run_id,
        generation_id=generation_id,
        generated_at=generated_at,
        metadata=metadata,
    )


def _initialize_serving_state(app: FastAPI) -> None:
    config: RecommenderConfig = app.state.config
    artifact = _load_production_artifact(config.artifacts_dir)
    model_version = _artifact_model_version(artifact, config.model_version)
    content_index = load_content_index(config.artifacts_dir) if config.content_enabled else None

    app.state.loaded_artifact = artifact
    app.state.content_index = content_index
    app.state.model_loaded = artifact is not None
    app.state.model_version = model_version
    app.state.content_index_loaded = content_index is not None

    logger.info(
        "recommender_startup model_loaded=%s model_version=%s artifact_dir=%s model_type=%s content_index_loaded=%s",
        app.state.model_loaded,
        model_version or "",
        config.artifacts_dir,
        config.model_type,
        app.state.content_index_loaded,
    )


def _artifact_model_version(artifact: LoadedArtifact | None, default: str) -> str | None:
    if artifact is None:
        return None
    return str(artifact.metadata.get("model_version") or default)


def _load_production_artifact(artifacts_dir: Path) -> LoadedArtifact | None:
    try:
        artifact = load_artifacts(artifacts_dir)
    except FileNotFoundError:
        return None
    if str(artifact.get("model_type") or "") != MODEL_TYPE:
        logger.warning("Ignoring non-production recommender artifact model_type=%s", artifact.get("model_type"))
        return None
    raw_schema = artifact.get("feature_schema")
    if not isinstance(raw_schema, dict):
        logger.warning("Ignoring recommender artifact without CatBoost feature_schema")
        return None
    metadata_path = artifacts_dir / METADATA_FILENAME
    metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else {}
    feature_schema = FeatureSchema(
        version=str(raw_schema["version"]),
        numeric_features=[str(item) for item in raw_schema["numeric_features"]],
        categorical_features=[str(item) for item in raw_schema["categorical_features"]],
    )
    model_artifact = CatBoostRankerArtifact(
        model=artifact["model"],
        trained=bool(artifact["trained"]),
        feature_schema=feature_schema,
        hyperparameters=artifact.get("hyperparameters", {}),
    )
    return LoadedArtifact(model_artifact=model_artifact, metadata=metadata)


def _empty_response(status: str, generation_id: str, generated_at: str) -> ThreadRecommendationResponse:
    return ThreadRecommendationResponse(
        status=status,
        recommendations=[],
        generation_id=generation_id,
        generated_at=generated_at,
    )


app = create_app()


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve Papaya recommendations over FastAPI")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--env-file", default=None)
    args = parser.parse_args()
    if args.env_file:
        config = RecommenderConfig.from_env(args.env_file)
        global app
        app = create_app(config)

    import uvicorn

    uvicorn.run(app, host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
