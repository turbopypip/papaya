from __future__ import annotations

from datetime import datetime, timezone
import json
from uuid import uuid4
from typing import Any

import polars as pl


def create_run(client, model_version: str, status: str = "running") -> str:
    run_id = str(uuid4())
    now = datetime.now(timezone.utc)
    client.insert(
        "recommendation_runs",
        [[run_id, model_version, now, None, 0, 0, "{}", status, "", now]],
        column_names=[
            "id",
            "model_version",
            "started_at",
            "finished_at",
            "users_count",
            "recommendations_count",
            "metrics",
            "status",
            "error",
            "created_at",
        ],
    )
    return run_id


def finish_run(
    client,
    run_id: str,
    model_version: str,
    users_count: int,
    recommendations_count: int,
    metrics: dict[str, Any] | None,
    status: str,
    error: str = "",
) -> None:
    now = datetime.now(timezone.utc)
    client.insert(
        "recommendation_runs",
        [[run_id, model_version, now, now, users_count, recommendations_count, json.dumps(metrics or {}), status, error, now]],
        column_names=[
            "id",
            "model_version",
            "started_at",
            "finished_at",
            "users_count",
            "recommendations_count",
            "metrics",
            "status",
            "error",
            "created_at",
        ],
    )


def write_recommendation_history(client, recommendations: dict[str, list[tuple[str, float, str]]], model_version: str, run_id: str) -> int:
    generated_at = datetime.now(timezone.utc)
    rows = []
    for user_id, items in recommendations.items():
        for rank, (thread_id, score, source) in enumerate(items, start=1):
            rows.append([str(uuid4()), user_id, thread_id, float(score), model_version, run_id, generated_at, rank, source])
    if not rows:
        return 0
    client.insert(
        "recommendation_history",
        rows,
        column_names=[
            "id",
            "user_id",
            "thread_id",
            "score",
            "model_version",
            "run_id",
            "generated_at",
            "rank",
            "source",
        ],
    )
    return len(rows)


def relevant_threads_by_user(test_interactions: pl.DataFrame) -> dict[str, set[str]]:
    if test_interactions.is_empty():
        return {}
    result: dict[str, set[str]] = {}
    for row in test_interactions.select("user_id", "thread_id").iter_rows(named=True):
        result.setdefault(row["user_id"], set()).add(row["thread_id"])
    return result


def thread_categories(threads: pl.DataFrame) -> dict[str, set[str]]:
    if threads.is_empty():
        return {}
    return {
        row["thread_id"]: set(row["categories"] or [])
        for row in threads.select("thread_id", "categories").iter_rows(named=True)
    }
