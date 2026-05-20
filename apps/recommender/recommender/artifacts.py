from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import json

import joblib

from recommender.config import RecommenderConfig
from recommender.content import ContentIndex
from recommender.matrix import InteractionMatrix
from recommender.modeling import ModelResult


ARTIFACT_FILENAME = "model.joblib"
METADATA_FILENAME = "metadata.json"


def save_artifacts(
    config: RecommenderConfig,
    model_result: ModelResult,
    interaction_matrix: InteractionMatrix,
    metrics: dict[str, object],
    params: dict[str, object],
    content_index: ContentIndex | None = None,
) -> Path:
    config.artifacts_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = config.artifacts_dir / ARTIFACT_FILENAME
    payload = {
        "model": model_result.model,
        "model_type": model_result.model_type,
        "trained": model_result.trained,
        "hyperparameters": model_result.hyperparameters or {},
        "champion_status": params.get("champion_status", "champion"),
        "user_to_index": interaction_matrix.user_to_index,
        "thread_to_index": interaction_matrix.thread_to_index,
        "index_to_user": interaction_matrix.index_to_user,
        "index_to_thread": interaction_matrix.index_to_thread,
        "matrix": interaction_matrix.matrix,
        "content_enabled": content_index is not None,
    }
    joblib.dump(payload, artifact_path)

    metadata = {
        "model_version": config.model_version,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "metrics": metrics,
        "params": params,
        "config": {
            key: str(value) if isinstance(value, Path) else value
            for key, value in asdict(config).items()
            if "password" not in key and "dsn" not in key and "url" not in key
        },
    }
    (config.artifacts_dir / METADATA_FILENAME).write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
    return artifact_path


def load_artifacts(artifacts_dir: Path) -> dict[str, object]:
    return joblib.load(artifacts_dir / ARTIFACT_FILENAME)
