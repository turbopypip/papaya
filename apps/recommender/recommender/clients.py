from __future__ import annotations

from sqlalchemy import create_engine

from recommender.config import RecommenderConfig


def create_postgres_engine(config: RecommenderConfig):
    return create_engine(config.postgres_dsn, pool_pre_ping=True)


def create_clickhouse_client(config: RecommenderConfig):
    import clickhouse_connect

    return clickhouse_connect.get_client(
        host=config.clickhouse_host,
        port=config.clickhouse_port,
        username=config.clickhouse_user,
        password=config.clickhouse_password,
        database=config.clickhouse_database,
    )
