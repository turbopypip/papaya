from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from typing import Any
from uuid import NAMESPACE_URL, uuid5

import polars as pl
from sqlalchemy import text

from recommender.clients import create_clickhouse_client, create_postgres_engine
from recommender.config import RecommenderConfig
from recommender.data import BehaviorData, BusinessData
from recommender.synthetic import BIG_TEST_SEED, SyntheticForumDataset, SyntheticScale, generate_synthetic_forum_dataset

DEMO_PASSWORD = "PapayaDemo1!"
DEMO_PASSWORD_HASH = "$2a$10$627IVlwxlqAdQ.5xWBt3uOvhbmV42rrXWS7oBh.XT4PUjTCAywNES"
DEMO_USERS_BY_PROFILE = {
    "backend-heavy": "backend-user",
    "frontend-heavy": "frontend-user",
    "devops-heavy": "devops-user",
    "mixed-fullstack": "mixed-user",
}


@dataclass(frozen=True)
class SyntheticStorageDataset:
    business: BusinessData
    behavior: BehaviorData
    source_to_storage_id: dict[str, dict[str, str]]
    dataset_id: str
    run_id: str


@dataclass(frozen=True)
class SyntheticLoadReport:
    dataset_id: str
    run_id: str
    users: int
    threads: int
    posts: int
    comments: int
    likes: int
    events: int
    user_thread_daily: int
    recommendation_daily: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "run_id": self.run_id,
            "users": self.users,
            "threads": self.threads,
            "posts": self.posts,
            "comments": self.comments,
            "likes": self.likes,
            "events": self.events,
            "user_thread_daily": self.user_thread_daily,
            "recommendation_daily": self.recommendation_daily,
        }


def storage_uuid(dataset_id: str, kind: str, source_id: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"papaya:{dataset_id}:{kind}:{source_id}"))


def materialize_storage_dataset(
    dataset: SyntheticForumDataset,
    dataset_id: str = "synthetic-big-test",
    run_id: str = "synthetic-run",
) -> SyntheticStorageDataset:
    users = dataset.business.users
    threads = dataset.business.threads
    posts = dataset.business.posts
    comments = dataset.business.comments
    likes = dataset.business.likes

    mappings = {
        "users": {row["user_id"]: storage_uuid(dataset_id, "user", row["user_id"]) for row in users.iter_rows(named=True)},
        "threads": {row["thread_id"]: storage_uuid(dataset_id, "thread", row["thread_id"]) for row in threads.iter_rows(named=True)},
        "posts": {row["post_id"]: storage_uuid(dataset_id, "post", row["post_id"]) for row in posts.iter_rows(named=True)},
        "comments": {row["comment_id"]: storage_uuid(dataset_id, "comment", row["comment_id"]) for row in comments.iter_rows(named=True)},
        "likes": {row["like_id"]: storage_uuid(dataset_id, "like", row["like_id"]) for row in likes.iter_rows(named=True)},
    }

    demo_usernames = _demo_usernames(dataset)
    storage_business = BusinessData(
        users=users.with_columns(
            pl.col("user_id").replace(mappings["users"]),
            pl.col("user_id")
            .map_elements(
                lambda user_id: demo_usernames.get(user_id),
                return_dtype=pl.Utf8,
            )
            .fill_null(pl.lit(f"synthetic_{dataset_id}_") + pl.col("username"))
            .alias("username"),
        ),
        threads=threads.with_columns(
            pl.col("thread_id").replace(mappings["threads"]),
            pl.col("author_user_id").replace(mappings["users"]),
        ),
        posts=posts.with_columns(
            pl.col("post_id").replace(mappings["posts"]),
            pl.col("thread_id").replace(mappings["threads"]),
            pl.col("user_id").replace(mappings["users"]),
        ),
        comments=comments.with_columns(
            pl.col("comment_id").replace(mappings["comments"]),
            pl.col("post_id").replace(mappings["posts"]),
            pl.col("thread_id").replace(mappings["threads"]),
            pl.col("user_id").replace(mappings["users"]),
        ),
        likes=likes.with_columns(
            pl.col("like_id").replace(mappings["likes"]),
            pl.col("user_id").replace(mappings["users"]),
            pl.when(pl.col("likable_type") == "comment")
            .then(pl.col("likable_id").replace(mappings["comments"]))
            .otherwise(pl.col("likable_id").replace(mappings["posts"]))
            .alias("likable_id"),
            pl.col("thread_id").replace(mappings["threads"]),
        ),
    )

    storage_events = dataset.behavior.events.with_columns(
        pl.col("user_id").replace(mappings["users"]),
        pl.when(pl.col("entity_type") == "thread")
        .then(pl.col("entity_id").replace(mappings["threads"]))
        .when(pl.col("entity_type") == "post")
        .then(pl.col("entity_id").replace(mappings["posts"]))
        .when(pl.col("entity_type") == "comment")
        .then(pl.col("entity_id").replace(mappings["comments"]))
        .otherwise(pl.col("entity_id"))
        .alias("entity_id"),
        pl.col("thread_id").replace(mappings["threads"]),
        pl.col("metadata").map_elements(
            lambda value: _metadata_with_fixture(value, dataset_id, run_id),
            return_dtype=pl.Utf8,
        ),
    )
    storage_behavior = BehaviorData(
        events=storage_events,
        user_thread_daily=dataset.behavior.user_thread_daily.with_columns(
            pl.col("user_id").replace(mappings["users"]),
            pl.col("thread_id").replace(mappings["threads"]),
        ),
        recommendation_daily=dataset.behavior.recommendation_daily.with_columns(
            pl.col("user_id").replace(mappings["users"]),
            pl.col("thread_id").replace(mappings["threads"]),
        ),
    )
    return SyntheticStorageDataset(storage_business, storage_behavior, mappings, dataset_id, run_id)


def load_synthetic_dataset(
    postgres_engine,
    clickhouse_client,
    dataset: SyntheticForumDataset,
    dataset_id: str = "synthetic-big-test",
    run_id: str = "synthetic-run",
    clear_existing: bool = True,
) -> SyntheticLoadReport:
    storage_dataset = materialize_storage_dataset(dataset, dataset_id=dataset_id, run_id=run_id)
    if clear_existing:
        clear_synthetic_dataset(postgres_engine, clickhouse_client, storage_dataset)
    _insert_postgres_business_data(postgres_engine, storage_dataset)
    _insert_clickhouse_behavior_data(clickhouse_client, storage_dataset)
    return _load_report(storage_dataset)


def clear_synthetic_dataset(postgres_engine, clickhouse_client, storage_dataset: SyntheticStorageDataset) -> None:
    business = storage_dataset.business
    with postgres_engine.begin() as conn:
        _delete_by_ids(conn, "likes", "id", business.likes.get_column("like_id").to_list())
        _delete_by_ids(conn, "comments", "id", business.comments.get_column("comment_id").to_list())
        _delete_by_ids(conn, "posts", "id", business.posts.get_column("post_id").to_list())
        _delete_by_ids(conn, "threads", "id", business.threads.get_column("thread_id").to_list())
        _delete_by_ids(conn, "users", "id", business.users.get_column("user_id").to_list())

    where = f"metadata LIKE '%\"dataset_id\": \"{storage_dataset.dataset_id}\"%'"
    clickhouse_client.command(f"ALTER TABLE user_events DELETE WHERE {where}")
    user_ids = ", ".join(f"'{user_id}'" for user_id in storage_dataset.business.users.get_column("user_id").to_list())
    if user_ids:
        clickhouse_client.command(f"ALTER TABLE user_thread_event_daily DELETE WHERE user_id IN ({user_ids})")
        clickhouse_client.command(f"ALTER TABLE recommendation_event_daily DELETE WHERE user_id IN ({user_ids})")
        clickhouse_client.command(f"ALTER TABLE recommendation_history DELETE WHERE user_id IN ({user_ids})")
    if storage_dataset.dataset_id == "recommender-demo":
        clickhouse_client.command("ALTER TABLE recommendation_runs DELETE WHERE model_version = 'demo-synthetic-v1'")


def validate_loaded_synthetic_dataset(
    postgres_engine,
    clickhouse_client,
    storage_dataset: SyntheticStorageDataset,
) -> list[str]:
    expected = _load_report(storage_dataset)
    errors: list[str] = []
    pg_checks = {
        "users": ("users", "id", storage_dataset.business.users.get_column("user_id").to_list()),
        "threads": ("threads", "id", storage_dataset.business.threads.get_column("thread_id").to_list()),
        "posts": ("posts", "id", storage_dataset.business.posts.get_column("post_id").to_list()),
        "comments": ("comments", "id", storage_dataset.business.comments.get_column("comment_id").to_list()),
        "likes": ("likes", "id", storage_dataset.business.likes.get_column("like_id").to_list()),
    }
    with postgres_engine.connect() as conn:
        for name, (table, column, ids) in pg_checks.items():
            actual = _count_by_ids(conn, table, column, ids)
            if actual != getattr(expected, name):
                errors.append(f"PostgreSQL {table} expected {getattr(expected, name)}, got {actual}")

    events_count = _clickhouse_count_by_dataset(clickhouse_client, "user_events", storage_dataset.dataset_id)
    if events_count != expected.events:
        errors.append(f"ClickHouse user_events expected {expected.events}, got {events_count}")
    return errors


def _insert_postgres_business_data(postgres_engine, storage_dataset: SyntheticStorageDataset) -> None:
    business = storage_dataset.business
    role_id = storage_uuid(storage_dataset.dataset_id, "role", "synthetic-user")
    now = datetime.now(timezone.utc)
    with postgres_engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO roles (id, name, permissions, created_at, updated_at)
                VALUES (:id, :name, CAST(:permissions AS jsonb), :created_at, :updated_at)
                ON CONFLICT (name) DO UPDATE SET permissions = EXCLUDED.permissions, updated_at = EXCLUDED.updated_at
                """
            ),
            {
                "id": role_id,
                "name": f"synthetic-{storage_dataset.dataset_id}-user",
                "permissions": json.dumps(_synthetic_user_permissions(), sort_keys=True),
                "created_at": now,
                "updated_at": now,
            },
        )
        conn.execute(
            text(
                """
                INSERT INTO users (id, username, email, password_hash, role_id, created_at, updated_at)
                VALUES (:id, :username, :email, :password_hash, :role_id, :created_at, :updated_at)
                ON CONFLICT (id) DO NOTHING
                """
            ),
            [
                {
                    "id": row["user_id"],
                    "username": row["username"],
                    "email": _email_for_username(row["username"]),
                    "password_hash": DEMO_PASSWORD_HASH,
                    "role_id": role_id,
                    "created_at": row["created_at"],
                    "updated_at": row["created_at"],
                }
                for row in business.users.iter_rows(named=True)
            ],
        )
        conn.execute(
            text(
                """
                INSERT INTO threads (id, title, categories, user_id, created_at, updated_at)
                VALUES (:id, :title, :categories, :user_id, :created_at, :updated_at)
                ON CONFLICT (id) DO NOTHING
                """
            ),
            [
                {
                    "id": row["thread_id"],
                    "title": f"[synthetic:{storage_dataset.dataset_id}] {row['title']}",
                    "categories": row["categories"],
                    "user_id": row["author_user_id"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
                for row in business.threads.iter_rows(named=True)
            ],
        )
        conn.execute(
            text(
                """
                INSERT INTO posts (id, content, user_id, thread_id, created_at, updated_at)
                VALUES (:id, :content, :user_id, :thread_id, :created_at, :updated_at)
                ON CONFLICT (id) DO NOTHING
                """
            ),
            [
                {
                    "id": row["post_id"],
                    "content": row.get("content") or f"Synthetic post for {row['thread_id']}",
                    "user_id": row["user_id"],
                    "thread_id": row["thread_id"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
                for row in business.posts.iter_rows(named=True)
            ],
        )
        conn.execute(
            text(
                """
                INSERT INTO comments (id, content, user_id, post_id, created_at, updated_at)
                VALUES (:id, :content, :user_id, :post_id, :created_at, :updated_at)
                ON CONFLICT (id) DO NOTHING
                """
            ),
            [
                {
                    "id": row["comment_id"],
                    "content": row.get("content") or f"Synthetic comment for {row['post_id']}",
                    "user_id": row["user_id"],
                    "post_id": row["post_id"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
                for row in business.comments.iter_rows(named=True)
            ],
        )
        conn.execute(
            text(
                """
                INSERT INTO likes (id, user_id, likable_id, likable_type, created_at, updated_at)
                VALUES (:id, :user_id, :likable_id, :likable_type, :created_at, :updated_at)
                ON CONFLICT (id) DO NOTHING
                """
            ),
            [
                {
                    "id": row["like_id"],
                    "user_id": row["user_id"],
                    "likable_id": row["likable_id"],
                    "likable_type": row["likable_type"],
                    "created_at": row["created_at"],
                    "updated_at": row["created_at"],
                }
                for row in business.likes.iter_rows(named=True)
            ],
        )


def _insert_clickhouse_behavior_data(clickhouse_client, storage_dataset: SyntheticStorageDataset) -> None:
    behavior = storage_dataset.behavior
    _insert_partitioned(
        clickhouse_client,
        "user_events",
        [
            [
                row["user_id"],
                row["event_type"],
                row["entity_type"],
                row["entity_id"],
                row["thread_id"],
                row["metadata"],
                row["created_at"],
            ]
            for row in behavior.events.iter_rows(named=True)
        ],
        column_names=["user_id", "event_type", "entity_type", "entity_id", "thread_id", "metadata", "created_at"],
        partition_value_index=6,
    )
    _insert_partitioned(
        clickhouse_client,
        "user_thread_event_daily",
        [
            [
                row["event_date"],
                row["user_id"],
                row["thread_id"],
                row["event_type"],
                int(row["events_count"]),
            ]
            for row in behavior.user_thread_daily.iter_rows(named=True)
        ],
        column_names=["event_date", "user_id", "thread_id", "event_type", "events_count"],
        partition_value_index=0,
    )
    _insert_partitioned(
        clickhouse_client,
        "recommendation_event_daily",
        [
            [
                row["event_date"],
                row["user_id"],
                row["thread_id"],
                row["model_version"],
                int(row["impressions"]),
                int(row["clicks"]),
                int(float(row["avg_position"]) * float(row["impressions"])),
                int(row["impressions"]),
            ]
            for row in behavior.recommendation_daily.iter_rows(named=True)
        ],
        column_names=[
            "event_date",
            "user_id",
            "thread_id",
            "model_version",
            "impressions",
            "clicks",
            "position_sum",
            "position_events",
        ],
        partition_value_index=0,
    )


def _insert_partitioned(
    clickhouse_client,
    table: str,
    rows: list[list[Any]],
    *,
    column_names: list[str],
    partition_value_index: int,
) -> None:
    rows_by_partition: dict[str, list[list[Any]]] = defaultdict(list)
    for row in rows:
        rows_by_partition[_yyyymm(row[partition_value_index])].append(row)
    for partition_rows in rows_by_partition.values():
        clickhouse_client.insert(table, partition_rows, column_names=column_names)


def _yyyymm(value: Any) -> str:
    if isinstance(value, datetime):
        return value.strftime("%Y%m")
    return value.strftime("%Y%m")


def _load_report(storage_dataset: SyntheticStorageDataset) -> SyntheticLoadReport:
    behavior = storage_dataset.behavior
    return SyntheticLoadReport(
        dataset_id=storage_dataset.dataset_id,
        run_id=storage_dataset.run_id,
        users=storage_dataset.business.users.height,
        threads=storage_dataset.business.threads.height,
        posts=storage_dataset.business.posts.height,
        comments=storage_dataset.business.comments.height,
        likes=storage_dataset.business.likes.height,
        events=behavior.events.height,
        user_thread_daily=behavior.user_thread_daily.height,
        recommendation_daily=behavior.recommendation_daily.height,
    )


def _metadata_with_fixture(value: str, dataset_id: str, run_id: str) -> str:
    metadata = json.loads(value or "{}")
    metadata["dataset_id"] = dataset_id
    metadata["run_id"] = run_id
    return json.dumps(metadata, sort_keys=True)


def _delete_by_ids(conn, table: str, column: str, ids: list[str]) -> None:
    if ids:
        conn.execute(text(f"DELETE FROM {table} WHERE {column}::text = ANY(:ids)"), {"ids": ids})


def _count_by_ids(conn, table: str, column: str, ids: list[str]) -> int:
    if not ids:
        return 0
    return int(conn.execute(text(f"SELECT count(*) FROM {table} WHERE {column}::text = ANY(:ids)"), {"ids": ids}).scalar() or 0)


def _clickhouse_count_by_dataset(clickhouse_client, table: str, dataset_id: str) -> int:
    result = clickhouse_client.query(
        f"""
        SELECT count()
        FROM {table}
        WHERE JSONExtractString(metadata, 'dataset_id') = %(dataset_id)s
        """,
        parameters={"dataset_id": dataset_id},
    )
    return int(result.result_rows[0][0] if result.result_rows else 0)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load Papaya synthetic recommendation fixture into test stores")
    parser.add_argument("--env-file", default=None)
    parser.add_argument("--seed", type=int, default=BIG_TEST_SEED)
    parser.add_argument("--dataset-id", default="synthetic-big-test")
    parser.add_argument("--run-id", default="synthetic-loader-run")
    parser.add_argument("--mode", choices=["smoke", "big"], default="big")
    parser.add_argument("--skip-clear", action="store_true")
    parser.add_argument("--clear-only", action="store_true")
    parser.add_argument("--validate", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = RecommenderConfig.from_env(args.env_file)
    now = datetime(2026, 5, 19, 12, tzinfo=timezone.utc)
    scale = SyntheticScale.smoke() if args.mode == "smoke" else SyntheticScale()
    dataset = generate_synthetic_forum_dataset(scale=scale, seed=args.seed, now=now)
    postgres = create_postgres_engine(config)
    clickhouse = create_clickhouse_client(config)
    if args.clear_only:
        storage_dataset = materialize_storage_dataset(dataset, dataset_id=args.dataset_id, run_id=args.run_id)
        clear_synthetic_dataset(postgres, clickhouse, storage_dataset)
        print(
            json.dumps(
                {
                    "dataset_id": args.dataset_id,
                    "run_id": args.run_id,
                    "cleared": True,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    report = load_synthetic_dataset(
        postgres,
        clickhouse,
        dataset,
        dataset_id=args.dataset_id,
        run_id=args.run_id,
        clear_existing=not args.skip_clear,
    )
    print(json.dumps(report.as_dict(), indent=2, sort_keys=True))
    if args.validate:
        storage_dataset = materialize_storage_dataset(dataset, dataset_id=args.dataset_id, run_id=args.run_id)
        errors = validate_loaded_synthetic_dataset(postgres, clickhouse, storage_dataset)
        if errors:
            print(json.dumps({"validation_errors": errors}, indent=2, sort_keys=True))
            return 1
    return 0


def _demo_usernames(dataset: SyntheticForumDataset) -> dict[str, str]:
    demo_usernames: dict[str, str] = {}
    assigned_profiles: set[str] = set()
    for row in dataset.user_profiles.sort("user_id").iter_rows(named=True):
        profile = row["profile"]
        if profile in DEMO_USERS_BY_PROFILE and profile not in assigned_profiles:
            demo_usernames[row["user_id"]] = DEMO_USERS_BY_PROFILE[profile]
            assigned_profiles.add(profile)
    return demo_usernames


def _email_for_username(username: str) -> str:
    domain = "papaya.demo" if username in DEMO_USERS_BY_PROFILE.values() else "synthetic.local"
    return f"{username}@{domain}"


def _synthetic_user_permissions() -> dict[str, Any]:
    own_content = {
        "create": True,
        "read": True,
        "update_own": True,
        "update_any": False,
        "delete_own": True,
        "delete_any": False,
    }
    own_relation = {
        "create": True,
        "read": True,
        "update_own": False,
        "update_any": False,
        "delete_own": True,
        "delete_any": False,
    }
    return {
        "threads": own_content,
        "posts": own_content,
        "comments": own_content,
        "categories": own_content,
        "likes": own_relation,
        "attachments": own_relation,
        "users": {
            "create": False,
            "read": True,
            "update_own": True,
            "update_any": False,
            "delete_own": False,
            "delete_any": False,
            "ban": False,
        },
    }


if __name__ == "__main__":
    raise SystemExit(main())
