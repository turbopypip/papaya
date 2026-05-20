from __future__ import annotations

import argparse
import json
import logging
import sys
import traceback
from pathlib import Path
from time import perf_counter

from recommender.artifacts import save_artifacts
from recommender.champion import evaluate_and_select_champion, selection_to_metrics
from recommender.clients import create_clickhouse_client, create_postgres_engine
from recommender.config import RecommenderConfig
from recommender.content import build_or_load_content_index, performance_guardrails
from recommender.etl import prepare_data
from recommender.loaders import load_behavior_data, load_business_data
from recommender.matrix import build_interaction_matrix
from recommender.metrics import recommendation_daily_quality
from recommender.recommendations import generate_for_users
from recommender.serving import create_run, finish_run


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("train_model")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train Papaya thread recommendation model")
    parser.add_argument("--env-file", default=None)
    parser.add_argument("--events-days", type=int, default=180)
    parser.add_argument("--metrics-k", type=int, default=10)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = RecommenderConfig.from_env(args.env_file)
    clickhouse = create_clickhouse_client(config)
    run_id = create_run(clickhouse, config.model_version)
    metrics: dict[str, object] = {}
    try:
        postgres = create_postgres_engine(config)
        metrics = run_training(config, postgres, clickhouse, run_id, args.events_days, args.metrics_k)
        logger.info("Training completed run_id=%s metrics=%s", run_id, metrics)
        return 0
    except Exception as exc:
        logger.error("Training failed: %s", exc)
        logger.debug("%s", traceback.format_exc())
        try:
            finish_run(clickhouse, run_id, config.model_version, 0, 0, metrics, "failed", str(exc))
        except Exception:
            logger.exception("Failed to write failed run status")
        return 1


def run_training(
    config: RecommenderConfig,
    postgres,
    clickhouse,
    run_id: str,
    events_days: int,
    metrics_k: int,
) -> dict[str, object]:
    business = load_business_data(postgres)
    behavior = load_behavior_data(clickhouse, days=events_days)
    prepared = prepare_data(business, behavior, half_life_days=config.half_life_days)
    matrix = build_interaction_matrix(prepared.train_interactions)
    selection = evaluate_and_select_champion(
        matrix,
        business.users,
        business.threads,
        prepared.train_interactions,
        prepared.test_interactions,
        prepared.interactions,
        top_n=config.top_n,
        candidate_pool_size=config.candidate_pool_size,
        random_state=config.random_state,
        k=metrics_k,
        candidate_model_types=candidate_model_types(config),
    )
    model_result = selection.model_result
    content_index = build_or_load_content_index(
        business.threads,
        config.artifacts_dir,
        model_name=config.content_embedding_model,
    ) if config.content_enabled else None

    candidate_users = prepared.user_ids or business.users.get_column("user_id").to_list()
    generation_started = perf_counter()
    recommendations = generate_for_users(
        candidate_users,
        business.threads,
        prepared.train_interactions,
        matrix,
        model_result,
        top_n=config.top_n,
        candidate_pool_size=config.candidate_pool_size,
        min_model_interactions=config.min_model_interactions,
        content_index=content_index,
    )
    generation_seconds = perf_counter() - generation_started
    metrics = selection_to_metrics(selection)
    selected_candidate = next(
        (candidate for candidate in selection.candidates if candidate.model_type == selection.model_type),
        None,
    )
    if selected_candidate is not None:
        metrics.update(selected_candidate.metrics)
    metrics.update(recommendation_daily_quality(behavior.recommendation_daily))
    if content_index is not None:
        metrics["content_guardrails"] = performance_guardrails(
            content_index,
            generation_seconds,
            max_generation_seconds=config.content_max_generation_seconds,
        )
    save_artifacts(
        config,
        model_result,
        matrix,
        metrics,
        {
            "half_life_days": config.half_life_days,
            "top_n": config.top_n,
            "candidate_pool_size": config.candidate_pool_size,
            "model_version": config.model_version,
            "configured_model_type": config.model_type,
            "model_type": model_result.model_type,
            "hyperparameters": model_result.hyperparameters or {},
            "random_state": config.random_state,
            "champion_status": selection.status,
            "run_id": run_id,
            "content_enabled": content_index is not None,
            "content_embedding_backend": content_index.backend if content_index is not None else "",
            "content_search_backend": content_index.search_backend if content_index is not None else "",
        },
        content_index=content_index,
    )
    finish_run(
        clickhouse,
        run_id,
        config.model_version,
        users_count=len(candidate_users),
        recommendations_count=sum(len(items) for items in recommendations.values()),
        metrics=metrics,
        status="success",
    )
    return metrics


def candidate_model_types(config: RecommenderConfig) -> tuple[str, ...]:
    normalized = config.model_type.lower().replace("-", "_")
    if normalized in {"winner", "winner_model"}:
        winner = _winner_candidate_from_metadata(config.artifacts_dir)
        return (winner,) if winner is not None else _selection_candidate_types()
    if normalized in {"entity_feature", "entity", "entity_feature_sgd"}:
        return ("entity_feature",)
    if normalized in {"learning_to_rank", "ranker", "learning_to_rank_sgd"}:
        return ("learning_to_rank",)
    if normalized in {"factorization_machine", "fm", "lightfm", "factorization_machine_svd"}:
        return ("factorization_machine",)
    if normalized in {"two_tower", "two_tower_neural", "two_tower_dot", "neural"}:
        return ("two_tower",)
    if normalized in {"auto", "champion", "compare", "selection"}:
        return _selection_candidate_types()
    logger.warning("Unknown RECOMMENDER_MODEL_TYPE=%s; running winner selection candidates", config.model_type)
    return _selection_candidate_types()


def _selection_candidate_types() -> tuple[str, ...]:
    return ("entity_feature", "learning_to_rank", "factorization_machine", "two_tower")


def _winner_candidate_from_metadata(artifacts_dir: Path) -> str | None:
    metadata_path = artifacts_dir / "metadata.json"
    if not metadata_path.exists():
        return None
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not read winner metadata from %s: %s", metadata_path, exc)
        return None
    metrics = metadata.get("metrics", {})
    params = metadata.get("params", {})
    model_type = str(metrics.get("champion_model_type") or params.get("model_type") or "")
    return _candidate_request_for_model_type(model_type)


def _candidate_request_for_model_type(model_type: str) -> str | None:
    normalized = model_type.lower().replace("-", "_")
    mapping = {
        "entity_feature_sgd": "entity_feature",
        "entity_feature": "entity_feature",
        "learning_to_rank_sgd": "learning_to_rank",
        "learning_to_rank": "learning_to_rank",
        "factorization_machine_svd": "factorization_machine",
        "factorization_machine": "factorization_machine",
        "two_tower_dot": "two_tower",
        "two_tower": "two_tower",
    }
    winner = mapping.get(normalized)
    if winner is None and normalized:
        logger.warning("Stored champion model_type=%s is not a 9.2 winner candidate; rerunning selection", model_type)
    return winner


if __name__ == "__main__":
    sys.exit(main())
