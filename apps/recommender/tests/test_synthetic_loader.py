from datetime import datetime, timezone
import json

from recommender.synthetic import SyntheticScale, generate_synthetic_forum_dataset
from recommender.synthetic_loader import (
    DEMO_PASSWORD_HASH,
    load_synthetic_dataset,
    materialize_storage_dataset,
    storage_uuid,
)


class FakeConnection:
    def __init__(self):
        self.executions = []

    def execute(self, statement, parameters=None):
        self.executions.append((str(statement), parameters))
        return self

    def scalar(self):
        return 0


class FakeEngine:
    def __init__(self):
        self.connection = FakeConnection()

    def begin(self):
        return self

    def connect(self):
        return self

    def __enter__(self):
        return self.connection

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeClickHouse:
    def __init__(self):
        self.inserts = []
        self.commands = []

    def insert(self, table, rows, column_names):
        self.inserts.append({"table": table, "rows": rows, "column_names": column_names})

    def command(self, sql):
        self.commands.append(sql)


def test_materialize_storage_dataset_uses_stable_uuids_and_fixture_metadata():
    now = datetime(2026, 5, 19, 12, tzinfo=timezone.utc)
    dataset = generate_synthetic_forum_dataset(scale=SyntheticScale.smoke(), seed=7, now=now)

    storage = materialize_storage_dataset(dataset, dataset_id="unit", run_id="run-1")

    first_user = dataset.business.users.item(0, "user_id")
    assert storage.source_to_storage_id["users"][first_user] == storage_uuid("unit", "user", first_user)
    assert storage.business.users.item(0, "user_id") == storage_uuid("unit", "user", first_user)
    metadata = json.loads(storage.behavior.events.item(0, "metadata"))
    assert metadata["dataset_id"] == "unit"
    assert metadata["run_id"] == "run-1"


def test_materialize_storage_dataset_adds_demo_login_usernames():
    now = datetime(2026, 5, 19, 12, tzinfo=timezone.utc)
    dataset = generate_synthetic_forum_dataset(scale=SyntheticScale.smoke(), seed=7, now=now)

    storage = materialize_storage_dataset(dataset, dataset_id="unit", run_id="run-1")

    usernames = set(storage.business.users.get_column("username").to_list())
    assert {"backend-user", "frontend-user", "devops-user", "mixed-user"} <= usernames


def test_load_synthetic_dataset_writes_postgres_and_clickhouse_tables():
    now = datetime(2026, 5, 19, 12, tzinfo=timezone.utc)
    dataset = generate_synthetic_forum_dataset(scale=SyntheticScale.smoke(), seed=11, now=now)
    engine = FakeEngine()
    clickhouse = FakeClickHouse()

    report = load_synthetic_dataset(engine, clickhouse, dataset, dataset_id="unit-load", run_id="run-1")

    assert report.users == dataset.business.users.height
    assert report.events == dataset.behavior.events.height
    inserted_tables = {insert["table"] for insert in clickhouse.inserts}
    assert {"user_events", "user_thread_event_daily", "recommendation_event_daily"} <= inserted_tables
    event_rows = [
        row
        for insert in clickhouse.inserts
        if insert["table"] == "user_events"
        for row in insert["rows"]
    ]
    assert len(event_rows) == dataset.behavior.events.height
    assert any("INSERT INTO users" in sql for sql, _params in engine.connection.executions)
    assert any("INSERT INTO threads" in sql for sql, _params in engine.connection.executions)
    users_insert = next(
        params
        for sql, params in engine.connection.executions
        if "INSERT INTO users" in sql
    )
    assert any(row["email"] == "backend-user@papaya.demo" for row in users_insert)
    assert {row["password_hash"] for row in users_insert} == {DEMO_PASSWORD_HASH}
