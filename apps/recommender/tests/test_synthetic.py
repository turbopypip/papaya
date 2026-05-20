from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

import polars as pl

from recommender.etl import prepare_data
from recommender.synthetic import SyntheticScale, build_synthetic_big_test_report, generate_synthetic_forum_dataset, validate_synthetic_forum_dataset


RECOMMENDER_ROOT = Path(__file__).resolve().parents[1]


def test_synthetic_forum_dataset_matches_big_test_criteria():
    scale = SyntheticScale.smoke()
    dataset = generate_synthetic_forum_dataset(scale=scale, seed=7, now=datetime(2026, 5, 19, 12, tzinfo=timezone.utc))

    assert validate_synthetic_forum_dataset(dataset, scale=scale) == []
    assert dataset.report["users"] == scale.users
    assert dataset.report["threads"] == scale.threads
    assert scale.posts_min <= dataset.report["posts"] <= scale.posts_max
    assert scale.comments_min <= dataset.report["comments"] <= scale.comments_max
    assert scale.events_min <= dataset.report["events"] <= scale.events_max
    assert "content" in dataset.business.threads.columns
    assert dataset.thread_profiles.filter(pl.col("source") != "synthetic-template").height >= 100


def test_synthetic_dataset_uses_real_fixture_posts_and_comments(tmp_path):
    fixture = tmp_path / "fixture.jsonl"
    fixture.write_text(
        json.dumps(
            {
                "source": "Stack Exchange Data Dump",
                "source_url": "https://stackoverflow.com/questions/101",
                "license": "CC BY-SA 4.0",
                "attribution": "Stack Overflow question 101",
                "question_id": "101",
                "owner_source_id": "10",
                "topic": "backend",
                "title": "How do I tune PostgreSQL indexes from Go?",
                "tags": ["postgresql", "go"],
                "score": 7,
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-02T00:00:00",
                "content": "Real question body with query plan details.",
                "posts": [
                    {
                        "source_post_id": "101",
                        "role": "question",
                        "owner_source_id": "10",
                        "content": "Real question body with query plan details.",
                        "created_at": "2024-01-01T00:00:00",
                        "updated_at": "2024-01-02T00:00:00",
                        "source_url": "https://stackoverflow.com/questions/101",
                        "license": "CC BY-SA 4.0",
                        "attribution": "Stack Overflow question 101",
                    },
                    {
                        "source_post_id": "102",
                        "role": "answer",
                        "owner_source_id": "11",
                        "content": "Real answer body: use EXPLAIN ANALYZE and partial indexes.",
                        "created_at": "2024-01-01T01:00:00",
                        "updated_at": "2024-01-01T01:00:00",
                        "source_url": "https://stackoverflow.com/a/102",
                        "license": "CC BY-SA 4.0",
                        "attribution": "Stack Overflow answer 102",
                    },
                ],
                "comments": [
                    {
                        "source_comment_id": "201",
                        "source_post_id": "102",
                        "owner_source_id": "12",
                        "content": "Real comment: check table statistics too.",
                        "created_at": "2024-01-01T02:00:00",
                        "source_url": "https://stackoverflow.com/questions/101",
                        "license": "CC BY-SA 4.0",
                        "attribution": "Stack Overflow comment 201",
                    }
                ],
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    scale = SyntheticScale.smoke()
    dataset = generate_synthetic_forum_dataset(
        scale=scale,
        seed=7,
        now=datetime(2026, 5, 19, 12, tzinfo=timezone.utc),
        fixture_path=fixture,
    )

    assert validate_synthetic_forum_dataset(dataset, scale=scale) == []
    assert dataset.report["real_content"]["posts"] > 0
    assert dataset.report["real_content"]["comments"] > 0
    assert dataset.business.threads.filter(pl.col("content").str.contains("Real answer body")).height > 0
    assert dataset.business.posts.filter(pl.col("content").str.contains("EXPLAIN ANALYZE")).height > 0
    assert dataset.business.comments.filter(pl.col("content").str.contains("table statistics")).height > 0


def test_synthetic_forum_dataset_prepares_train_test_interactions():
    now = datetime(2026, 5, 19, 12, tzinfo=timezone.utc)
    dataset = generate_synthetic_forum_dataset(scale=SyntheticScale.smoke(), seed=11, now=now)

    prepared = prepare_data(dataset.business, dataset.behavior, half_life_days=21.0, now=now)

    assert prepared.interactions.height > dataset.business.users.height
    assert prepared.train_interactions.height > 0
    assert prepared.test_interactions.height > 0
    user_event_counts = prepared.interactions.group_by("user_id").agg(pl.sum("events_count").alias("events_count"))
    assert user_event_counts.filter(pl.col("events_count") < 30).is_empty()


def test_synthetic_report_evaluates_future_events_without_train_leakage():
    now = datetime(2026, 5, 19, 12, tzinfo=timezone.utc)
    scale = SyntheticScale.smoke()
    dataset = generate_synthetic_forum_dataset(scale=scale, seed=9400, now=now)

    report = build_synthetic_big_test_report(dataset, seed=9400, scale=scale, now=now)

    assert report["validation_errors"] == []
    assert report["split"]["train_interactions"] > 0
    assert report["split"]["test_interactions"] > 0
    assert report["split"]["evaluates_future_events_only"] is True
    assert report["split"]["leaked_user_thread_pairs"] == []
    assert report["split"]["test_users"] > 0


def test_synthetic_module_cli_writes_report(tmp_path):
    output = tmp_path / "synthetic-report.json"

    result = subprocess.run(
        [sys.executable, "-m", "recommender.synthetic", "--mode", "smoke", "--seed", "9400", "--output", str(output)],
        cwd=RECOMMENDER_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    report = json.loads(output.read_text())
    assert report["seed"] == 9400
    assert report["validation_errors"] == []
    assert report["split"]["evaluates_future_events_only"] is True
