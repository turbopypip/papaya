from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any

import polars as pl

from recommender.evaluation import baseline_recommendation_sets, evaluate_recommendation_sets, popularity_by_thread
from recommender.entity_model import (
    train_entity_feature_model,
    train_factorization_machine_model,
    train_learning_to_rank_model,
    train_two_tower_model,
)
from recommender.matrix import InteractionMatrix
from recommender.modeling import ModelResult, recommend_for_user
from recommender.recommendations import excluded_threads_for_user
from recommender.serving import thread_categories


ML_CANDIDATES = ("entity_feature", "learning_to_rank", "factorization_machine", "two_tower")
MODEL_COMPLEXITY_ORDER = {
    "entity_feature_sgd": 0,
    "learning_to_rank_sgd": 1,
    "factorization_machine_svd": 2,
    "two_tower_dot": 3,
}
CHAMPION_SCORE_WEIGHTS = {
    "ndcg_at_k": 0.45,
    "recall_at_k": 0.25,
    "map_at_k": 0.15,
    "coverage": 0.10,
    "diversity": 0.05,
}
TIE_BREAK_RELATIVE_DELTA = 0.03
MIN_COVERAGE = 0.01
MIN_DIVERSITY = 0.01
MIN_PERSONALIZATION = 0.01


@dataclass
class CandidateEvaluation:
    model_result: ModelResult | None
    model_type: str
    requested_model_type: str
    trained: bool
    hyperparameters: dict[str, object]
    metrics: dict[str, float]
    champion_score: float
    training_seconds: float
    generation_seconds: float
    recommendations_by_user: dict[str, list[str]]


@dataclass
class ChampionSelection:
    model_result: ModelResult
    model_type: str
    champion_score: float
    status: str
    reason: str
    candidates: list[CandidateEvaluation]
    baselines: dict[str, dict[str, float]]
    guardrails: dict[str, object]


def evaluate_and_select_champion(
    matrix: InteractionMatrix,
    users: pl.DataFrame,
    threads: pl.DataFrame,
    train_interactions: pl.DataFrame,
    test_interactions: pl.DataFrame,
    all_interactions: pl.DataFrame,
    top_n: int,
    candidate_pool_size: int,
    random_state: int,
    k: int,
    candidate_model_types: tuple[str, ...] | None = None,
) -> ChampionSelection:
    user_ids = users.get_column("user_id").to_list() if users.height else sorted(matrix.user_to_index)
    all_thread_ids = set(threads.get_column("thread_id").to_list()) if threads.height else set()
    categories = thread_categories(threads)
    popularity = popularity_by_thread(all_interactions)

    candidates = [
        _evaluate_candidate(
            requested_model_type=model_type,
            matrix=matrix,
            user_ids=user_ids,
            threads=threads,
            train_interactions=train_interactions,
            test_interactions=test_interactions,
            all_thread_ids=all_thread_ids,
            categories=categories,
            popularity=popularity,
            top_n=top_n,
            candidate_pool_size=candidate_pool_size,
            random_state=random_state,
            k=k,
        )
        for model_type in (candidate_model_types or ML_CANDIDATES)
    ]

    baselines = baseline_recommendation_sets(user_ids, threads, train_interactions, top_n=top_n)
    baseline_metrics = evaluate_recommendation_sets(
        baselines,
        test_interactions,
        all_thread_ids,
        categories,
        popularity,
        k=k,
    )
    return select_champion(candidates, baseline_metrics)


def select_champion(
    candidates: list[CandidateEvaluation],
    baselines: dict[str, dict[str, float]],
) -> ChampionSelection:
    trained_candidates = [candidate for candidate in candidates if candidate.trained and candidate.model_result is not None]
    if not trained_candidates:
        fallback = ModelResult(model=None, model_type="fallback", trained=False, hyperparameters={})
        return ChampionSelection(
            model_result=fallback,
            model_type=fallback.model_type,
            champion_score=0.0,
            status="fallback",
            reason="No 9.2 winner candidate could be trained; serving will use explicit fallback sources.",
            candidates=candidates,
            baselines=baselines,
            guardrails={"passed": False, "failures": ["no_trained_ml_candidate"]},
        )

    ranked = sorted(
        trained_candidates,
        key=lambda candidate: (
            candidate.champion_score,
            -MODEL_COMPLEXITY_ORDER.get(candidate.model_type, 99),
        ),
        reverse=True,
    )
    metric_best = ranked[0]
    best = metric_best
    for candidate in ranked[1:]:
        if _within_tie_band(best.champion_score, candidate.champion_score):
            best = min([best, candidate], key=lambda item: MODEL_COMPLEXITY_ORDER.get(item.model_type, 99))

    guardrails = _guardrails(best, baselines)
    status = "champion" if guardrails["passed"] else "champion_guardrail_failed"
    reason = _selection_reason(best, guardrails, metric_best if metric_best.model_type != best.model_type else None)
    return ChampionSelection(
        model_result=best.model_result or ModelResult(model=None, model_type="fallback", trained=False, hyperparameters={}),
        model_type=best.model_type,
        champion_score=best.champion_score,
        status=status,
        reason=reason,
        candidates=candidates,
        baselines=baselines,
        guardrails=guardrails,
    )


def selection_to_metrics(selection: ChampionSelection) -> dict[str, Any]:
    return {
        "champion_model_type": selection.model_type,
        "champion_score": selection.champion_score,
        "champion_status": selection.status,
        "champion_reason": selection.reason,
        "champion_guardrails": selection.guardrails,
        "ml_candidates": [
            {
                "model_type": candidate.model_type,
                "requested_model_type": candidate.requested_model_type,
                "trained": candidate.trained,
                "hyperparameters": candidate.hyperparameters,
                "metrics": candidate.metrics,
                "champion_score": candidate.champion_score,
                "training_seconds": candidate.training_seconds,
                "generation_seconds": candidate.generation_seconds,
            }
            for candidate in selection.candidates
        ],
        "baseline_comparison": selection.baselines,
    }


def render_champion_report(selection: ChampionSelection, k: int) -> str:
    lines = [
        "# Recommendation Champion Report",
        "",
        f"Primary metric: NDCG@{k}",
        "Champion score formula: 0.45*NDCG + 0.25*Recall + 0.15*MAP + 0.10*coverage + 0.05*diversity",
        f"Selected model: {selection.model_type}",
        f"Status: {selection.status}",
        f"Reason: {selection.reason}",
        "",
        "## ML Candidates",
        "",
        "| model | champion_score | ndcg | recall | map | coverage | diversity | train_s | generate_s |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for candidate in selection.candidates:
        metrics = candidate.metrics
        lines.append(
            "| {model} | {score:.6f} | {ndcg:.6f} | {recall:.6f} | {map_:.6f} | {coverage:.6f} | {diversity:.6f} | {train:.3f} | {generate:.3f} |".format(
                model=candidate.model_type,
                score=candidate.champion_score,
                ndcg=metrics.get("ndcg_at_k", 0.0),
                recall=metrics.get("recall_at_k", 0.0),
                map_=metrics.get("map_at_k", 0.0),
                coverage=metrics.get("coverage", 0.0),
                diversity=metrics.get("diversity", 0.0),
                train=candidate.training_seconds,
                generate=candidate.generation_seconds,
            )
        )
    lines.extend(["", "## Baselines", "", "| baseline | ndcg | recall | map | coverage | diversity |", "| --- | ---: | ---: | ---: | ---: | ---: |"])
    for name, metrics in sorted(selection.baselines.items()):
        lines.append(
            "| {name} | {ndcg:.6f} | {recall:.6f} | {map_:.6f} | {coverage:.6f} | {diversity:.6f} |".format(
                name=name,
                ndcg=metrics.get("ndcg_at_k", 0.0),
                recall=metrics.get("recall_at_k", 0.0),
                map_=metrics.get("map_at_k", 0.0),
                coverage=metrics.get("coverage", 0.0),
                diversity=metrics.get("diversity", 0.0),
            )
        )
    lines.extend(["", "## Guardrails", ""])
    for key, value in selection.guardrails.items():
        lines.append(f"- {key}: {value}")
    return "\n".join(lines) + "\n"


def _evaluate_candidate(
    requested_model_type: str,
    matrix: InteractionMatrix,
    user_ids: list[str],
    threads: pl.DataFrame,
    train_interactions: pl.DataFrame,
    test_interactions: pl.DataFrame,
    all_thread_ids: set[str],
    categories: dict[str, set[str]],
    popularity: dict[str, float],
    top_n: int,
    candidate_pool_size: int,
    random_state: int,
    k: int,
) -> CandidateEvaluation:
    train_started = perf_counter()
    normalized_model_type = requested_model_type.lower().replace("-", "_")
    if normalized_model_type in {"entity_feature", "entity"}:
        model_result = train_entity_feature_model(threads, train_interactions, matrix, random_state=random_state)
    elif normalized_model_type in {"learning_to_rank", "ranker", "lambdarank"}:
        model_result = train_learning_to_rank_model(threads, train_interactions, matrix, random_state=random_state)
    elif normalized_model_type in {"factorization_machine", "fm", "lightfm"}:
        model_result = train_factorization_machine_model(threads, train_interactions, matrix, random_state=random_state)
    elif normalized_model_type in {"two_tower", "two_tower_neural", "neural"}:
        model_result = train_two_tower_model(threads, train_interactions, matrix, random_state=random_state)
    else:
        model_result = ModelResult(model=None, model_type="fallback", trained=False, hyperparameters={})
    training_seconds = perf_counter() - train_started
    generate_started = perf_counter()
    recommendations = _model_recommendations_for_users(
        user_ids,
        threads,
        train_interactions,
        matrix,
        model_result,
        top_n=top_n,
        candidate_pool_size=candidate_pool_size,
    )
    generation_seconds = perf_counter() - generate_started
    metrics = evaluate_recommendation_sets(
        {model_result.model_type: recommendations},
        test_interactions,
        all_thread_ids,
        categories,
        popularity,
        k=k,
    )[model_result.model_type]
    metrics["training_seconds"] = training_seconds
    metrics["generation_seconds"] = generation_seconds
    score = champion_score(metrics)
    return CandidateEvaluation(
        model_result=model_result,
        model_type=model_result.model_type,
        requested_model_type=requested_model_type,
        trained=model_result.trained,
        hyperparameters=model_result.hyperparameters or {},
        metrics=metrics,
        champion_score=score,
        training_seconds=training_seconds,
        generation_seconds=generation_seconds,
        recommendations_by_user=recommendations,
    )


def _model_recommendations_for_users(
    user_ids: list[str],
    threads: pl.DataFrame,
    train_interactions: pl.DataFrame,
    matrix: InteractionMatrix,
    model_result: ModelResult,
    top_n: int,
    candidate_pool_size: int,
) -> dict[str, list[str]]:
    output: dict[str, list[str]] = {}
    for user_id in user_ids:
        exclude = excluded_threads_for_user(user_id, train_interactions, threads)
        output[user_id] = [
            thread_id
            for thread_id, _score in recommend_for_user(model_result, matrix, user_id, max(candidate_pool_size, top_n), exclude)
        ][:top_n]
    return output


def champion_score(metrics: dict[str, float]) -> float:
    return sum(float(metrics.get(metric, 0.0)) * weight for metric, weight in CHAMPION_SCORE_WEIGHTS.items())


def _within_tie_band(best_score: float, candidate_score: float) -> bool:
    if best_score == candidate_score:
        return True
    threshold = max(abs(best_score), abs(candidate_score), 1e-9) * TIE_BREAK_RELATIVE_DELTA
    return abs(best_score - candidate_score) <= threshold


def _guardrails(candidate: CandidateEvaluation, baselines: dict[str, dict[str, float]]) -> dict[str, object]:
    best_baseline_ndcg = max((metrics.get("ndcg_at_k", 0.0) for metrics in baselines.values()), default=0.0)
    best_baseline_recall = max((metrics.get("recall_at_k", 0.0) for metrics in baselines.values()), default=0.0)
    metrics = candidate.metrics
    failures = []
    if metrics.get("ndcg_at_k", 0.0) < best_baseline_ndcg:
        failures.append("below_baseline_ndcg")
    if metrics.get("recall_at_k", 0.0) < best_baseline_recall:
        failures.append("below_baseline_recall")
    if metrics.get("coverage", 0.0) < MIN_COVERAGE:
        failures.append("low_coverage")
    if metrics.get("diversity", 0.0) < MIN_DIVERSITY:
        failures.append("low_diversity")
    if metrics.get("personalization", 0.0) < MIN_PERSONALIZATION:
        failures.append("low_personalization")
    return {
        "passed": not failures,
        "failures": failures,
        "best_baseline_ndcg_at_k": best_baseline_ndcg,
        "best_baseline_recall_at_k": best_baseline_recall,
        "min_coverage": MIN_COVERAGE,
        "min_diversity": MIN_DIVERSITY,
        "min_personalization": MIN_PERSONALIZATION,
    }


def _selection_reason(
    candidate: CandidateEvaluation,
    guardrails: dict[str, object],
    metric_best: CandidateEvaluation | None = None,
) -> str:
    details = [
        f"selected by champion_score={candidate.champion_score:.6f}",
        f"ndcg_at_k={candidate.metrics.get('ndcg_at_k', 0.0):.6f}",
        f"recall_at_k={candidate.metrics.get('recall_at_k', 0.0):.6f}",
    ]
    if metric_best is not None:
        details.append(
            "within 3% tie band of "
            f"{metric_best.model_type} champion_score={metric_best.champion_score:.6f}; simpler winner chosen"
        )
    if guardrails["passed"]:
        details.append("all guardrails passed")
    else:
        details.append(f"guardrails failed: {', '.join(guardrails['failures'])}")
    return "; ".join(details)
