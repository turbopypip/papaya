from __future__ import annotations

import argparse
import logging
import sys
import traceback
from time import perf_counter

from recommender.artifacts import save_catboost_artifacts
from recommender.catboost_ranker import (
    MODEL_TYPE,
    evaluate_catboost_ranker,
    generate_catboost_for_users,
    train_catboost_ranker,
)
from recommender.clients import create_clickhouse_client, create_postgres_engine
from recommender.config import RecommenderConfig
from recommender.content import build_or_load_content_index, performance_guardrails
from recommender.etl import prepare_data
from recommender.loaders import load_behavior_data, load_business_data
from recommender.metrics import recommendation_daily_quality
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
    model_artifact = train_catboost_ranker(
        business,
        prepared.train_interactions,
        random_state=config.random_state,
        top_n=config.top_n,
    )
    content_index = build_or_load_content_index(
        business.threads,
        config.artifacts_dir,
        model_name=config.content_embedding_model,
    ) if config.content_enabled else None

    candidate_users = prepared.user_ids or business.users.get_column("user_id").to_list()
    generation_started = perf_counter()
    recommendations = generate_catboost_for_users(
        candidate_users,
        business,
        prepared.train_interactions,
        top_n=config.top_n,
        candidate_pool_size=config.candidate_pool_size,
        min_model_interactions=config.min_model_interactions,
        artifact=model_artifact,
    )
    generation_seconds = perf_counter() - generation_started
    metrics = evaluate_catboost_ranker(
        model_artifact,
        business,
        prepared.train_interactions,
        prepared.test_interactions,
        top_n=config.top_n,
        candidate_pool_size=config.candidate_pool_size,
        min_model_interactions=config.min_model_interactions,
        k=metrics_k,
    )
    metrics.update(recommendation_daily_quality(behavior.recommendation_daily))
    metrics.update(
        {
            "model_type": MODEL_TYPE,
            "model_trained": model_artifact.trained,
            "feature_schema_version": model_artifact.feature_schema.version,
            "training_rows": float(model_artifact.hyperparameters.get("training_rows", 0.0)),
            "training_groups": float(model_artifact.hyperparameters.get("training_groups", 0.0)),
            "generated_recommendations": float(sum(len(items) for items in recommendations.values())),
        }
    )
    if content_index is not None:
        metrics["content_guardrails"] = performance_guardrails(
            content_index,
            generation_seconds,
            max_generation_seconds=config.content_max_generation_seconds,
        )
    save_catboost_artifacts(
        config,
        model_artifact,
        metrics,
        {
            "half_life_days": config.half_life_days,
            "top_n": config.top_n,
            "candidate_pool_size": config.candidate_pool_size,
            "model_version": config.model_version,
            "configured_model_type": MODEL_TYPE,
            "model_type": MODEL_TYPE,
            "hyperparameters": model_artifact.hyperparameters or {},
            "random_state": config.random_state,
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


if __name__ == "__main__":
    sys.exit(main())
