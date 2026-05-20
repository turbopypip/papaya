from __future__ import annotations

import argparse
import logging
import sys
import traceback
from time import perf_counter

from recommender.artifacts import load_artifacts
from recommender.clients import create_clickhouse_client, create_postgres_engine
from recommender.config import RecommenderConfig
from recommender.content import build_or_load_content_index, load_content_index, performance_guardrails
from recommender.etl import prepare_data
from recommender.loaders import load_behavior_data, load_business_data
from recommender.matrix import InteractionMatrix
from recommender.metrics import recommendation_daily_quality
from recommender.modeling import ModelResult
from recommender.recommendations import generate_for_users
from recommender.serving import create_run, finish_run, write_recommendation_history


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("generate_recommendations")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Papaya thread recommendations")
    parser.add_argument("--env-file", default=None)
    parser.add_argument("--events-days", type=int, default=180)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = RecommenderConfig.from_env(args.env_file)
    clickhouse = create_clickhouse_client(config)
    run_id = create_run(clickhouse, config.model_version)
    try:
        postgres = create_postgres_engine(config)
        metrics = run_generation(config, postgres, clickhouse, run_id, args.events_days)
        logger.info("Generated recommendations run_id=%s metrics=%s", run_id, metrics)
        return 0
    except Exception as exc:
        logger.error("Recommendation generation failed: %s", exc)
        logger.debug("%s", traceback.format_exc())
        try:
            finish_run(clickhouse, run_id, config.model_version, 0, 0, {}, "failed", str(exc))
        except Exception:
            logger.exception("Failed to write failed run status")
        return 1


def run_generation(
    config: RecommenderConfig,
    postgres,
    clickhouse,
    run_id: str,
    events_days: int,
) -> dict[str, object]:
    business = load_business_data(postgres)
    behavior = load_behavior_data(clickhouse, days=events_days)
    prepared = prepare_data(business, behavior, half_life_days=config.half_life_days)

    artifact = load_artifacts(config.artifacts_dir)
    matrix = InteractionMatrix(
        matrix=artifact["matrix"],
        user_to_index=artifact["user_to_index"],
        thread_to_index=artifact["thread_to_index"],
        index_to_user=artifact["index_to_user"],
        index_to_thread=artifact["index_to_thread"],
    )
    model_result = ModelResult(
        model=artifact["model"],
        model_type=artifact["model_type"],
        trained=bool(artifact["trained"]),
        hyperparameters=artifact.get("hyperparameters", {}),
    )
    content_index = None
    if config.content_enabled:
        content_index = load_content_index(config.artifacts_dir)
        if content_index is None:
            content_index = build_or_load_content_index(
                business.threads,
                config.artifacts_dir,
                model_name=config.content_embedding_model,
            )
    user_ids = business.users.get_column("user_id").to_list() if business.users.height else prepared.user_ids
    generation_started = perf_counter()
    recommendations = generate_for_users(
        user_ids,
        business.threads,
        prepared.interactions,
        matrix,
        model_result,
        top_n=config.top_n,
        candidate_pool_size=config.candidate_pool_size,
        min_model_interactions=config.min_model_interactions,
        content_index=content_index,
    )
    generation_seconds = perf_counter() - generation_started
    history_count = write_recommendation_history(clickhouse, recommendations, config.model_version, run_id)
    metrics = {
        "history_recommendations": float(history_count),
        "model_type": model_result.model_type,
        "champion_status": str(artifact.get("champion_status", "champion")),
    }
    if content_index is not None:
        metrics["content_guardrails"] = performance_guardrails(
            content_index,
            generation_seconds,
            max_generation_seconds=config.content_max_generation_seconds,
        )
    metrics.update(recommendation_daily_quality(behavior.recommendation_daily))
    finish_run(
        clickhouse,
        run_id,
        config.model_version,
        users_count=len(user_ids),
        recommendations_count=history_count,
        metrics=metrics,
        status="success",
    )
    return metrics


if __name__ == "__main__":
    sys.exit(main())
