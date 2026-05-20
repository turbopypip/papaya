from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import argparse
import json
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI
from pydantic import BaseModel, Field

from recommender.artifacts import METADATA_FILENAME, load_artifacts
from recommender.clients import create_clickhouse_client, create_postgres_engine
from recommender.config import RecommenderConfig
from recommender.content import load_content_index
from recommender.etl import prepare_data
from recommender.loaders import load_behavior_data, load_business_data
from recommender.matrix import InteractionMatrix
from recommender.modeling import ModelResult
from recommender.recommendations import generate_for_users


STATUS_READY = "ready"
STATUS_MODEL_NOT_READY = "model_not_ready"
STATUS_NO_RECOMMENDATIONS = "no_recommendations"


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
    matrix: InteractionMatrix
    model_result: ModelResult
    metadata: dict[str, object]


def create_app(config: RecommenderConfig | None = None) -> FastAPI:
    app = FastAPI(title="Papaya Recommender", version="0.1.0")
    app.state.config = config or RecommenderConfig.from_env()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/recommendations/threads", response_model=ThreadRecommendationResponse)
    def recommend_threads(payload: ThreadRecommendationRequest) -> ThreadRecommendationResponse:
        return generate_thread_recommendations(app.state.config, payload)

    return app


app = create_app()


def generate_thread_recommendations(
    config: RecommenderConfig,
    payload: ThreadRecommendationRequest,
) -> ThreadRecommendationResponse:
    generation_id = str(uuid4())
    generated_at = datetime.now(timezone.utc).isoformat()
    artifact = _load_winner_artifact(config.artifacts_dir)
    if artifact is None:
        return _empty_response(STATUS_MODEL_NOT_READY, generation_id, generated_at)

    postgres = create_postgres_engine(config)
    clickhouse = create_clickhouse_client(config)
    business = load_business_data(postgres)
    behavior = load_behavior_data(clickhouse, days=payload.events_days)
    prepared = prepare_data(business, behavior, half_life_days=config.half_life_days)

    content_index = load_content_index(config.artifacts_dir) if config.content_enabled else None
    recommendations = generate_for_users(
        [payload.user_id],
        business.threads,
        prepared.interactions,
        artifact.matrix,
        artifact.model_result,
        top_n=payload.limit,
        candidate_pool_size=max(config.candidate_pool_size, payload.limit),
        min_model_interactions=config.min_model_interactions,
        content_index=content_index,
    ).get(payload.user_id, [])

    model_version = str(artifact.metadata.get("model_version") or config.model_version)
    params = artifact.metadata.get("params", {}) if isinstance(artifact.metadata.get("params"), dict) else {}
    run_id = str(params.get("run_id") or "") or None
    metadata = {
        "model_type": artifact.model_result.model_type,
        "champion_status": str(artifact.metadata.get("champion_status") or params.get("champion_status") or "champion"),
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


def _load_winner_artifact(artifacts_dir: Path) -> LoadedArtifact | None:
    try:
        artifact = load_artifacts(artifacts_dir)
    except FileNotFoundError:
        return None
    metadata_path = artifacts_dir / METADATA_FILENAME
    metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else {}
    matrix = InteractionMatrix(
        matrix=artifact["matrix"],
        user_to_index=artifact["user_to_index"],
        thread_to_index=artifact["thread_to_index"],
        index_to_user=artifact["index_to_user"],
        index_to_thread=artifact["index_to_thread"],
    )
    model_result = ModelResult(
        model=artifact["model"],
        model_type=str(artifact["model_type"]),
        trained=bool(artifact["trained"]),
        hyperparameters=artifact.get("hyperparameters", {}),
    )
    return LoadedArtifact(matrix=matrix, model_result=model_result, metadata=metadata)


def _empty_response(status: str, generation_id: str, generated_at: str) -> ThreadRecommendationResponse:
    return ThreadRecommendationResponse(
        status=status,
        recommendations=[],
        generation_id=generation_id,
        generated_at=generated_at,
    )


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
