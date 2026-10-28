import sqlite3
from pathlib import Path

from sqlalchemy import create_engine, event, inspect
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


INITIAL_REVISION = "0001_initial_schema"
CURRENT_LEGACY_REVISION = "0002_generation_timing_and_tokens"


class Database:
    def __init__(self, url: str) -> None:
        self.url = url
        if url.startswith("sqlite:///") and ":memory:" not in url:
            Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        self.engine = create_engine(url, connect_args=connect_args)
        if url.startswith("sqlite"):
            event.listen(self.engine, "connect", self._enable_sqlite_foreign_keys)
        self.sessions = sessionmaker(self.engine, expire_on_commit=False, class_=Session)

    @staticmethod
    def _enable_sqlite_foreign_keys(dbapi_connection, _) -> None:
        if isinstance(dbapi_connection, sqlite3.Connection):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    def create_all(self) -> None:
        Base.metadata.create_all(self.engine)

    def migrate(self) -> None:
        from alembic import command
        from alembic.config import Config

        from app.config import PROJECT_ROOT

        config = Config(str(PROJECT_ROOT / "alembic.ini"))
        with self.engine.begin() as connection:
            existing_tables = set(inspect(connection).get_table_names())
            config.attributes["connection"] = connection
            if not existing_tables:
                command.upgrade(config, "head")
            elif "alembic_version" not in existing_tables:
                plan_columns = {column["name"] for column in inspect(connection).get_columns("learning_plans")}
                baseline = (
                    CURRENT_LEGACY_REVISION if {"started_at", "token_usage"} <= plan_columns else INITIAL_REVISION
                )
                command.stamp(config, baseline)
                command.upgrade(config, "head")
            else:
                command.upgrade(config, "head")

    def close(self) -> None:
        self.engine.dispose()
