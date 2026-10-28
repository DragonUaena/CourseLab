from pathlib import Path

from sqlalchemy import func, select, text

from app.database import Database
from app.models import LearningPlan, User


def test_migrations_create_schema_and_enable_sqlite_foreign_keys(tmp_path: Path):
    database = Database(f"sqlite:///{(tmp_path / 'migrated.db').as_posix()}")
    database.migrate()
    with database.engine.connect() as connection:
        assert connection.scalar(text("PRAGMA foreign_keys")) == 1
        table_names = {
            row[0] for row in connection.execute(text("SELECT name FROM sqlite_master WHERE type = 'table'"))
        }
        plan_columns = {row[1] for row in connection.execute(text("PRAGMA table_info(learning_plans)"))}
    assert {"alembic_version", "users", "user_credentials", "learning_plans"} <= table_names
    assert {"started_at", "token_usage"} <= plan_columns

    with database.sessions() as session:
        user = User(email="cascade@example.com", display_name="Cascade", password_hash="hash")
        session.add(user)
        session.flush()
        session.add(
            LearningPlan(
                user_id=user.id,
                topic="外键测试",
                goal="确认删除用户时数据库会级联删除学习计划",
                level="入门",
                weekly_hours=2,
                duration_weeks=1,
                language="中文",
            )
        )
        session.commit()

    with database.engine.begin() as connection:
        connection.execute(text("DELETE FROM users"))
    with database.sessions() as session:
        assert session.scalar(select(func.count()).select_from(LearningPlan)) == 0
    database.close()
