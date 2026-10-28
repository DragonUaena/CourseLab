"""Add generation timing and token usage metadata.

Revision ID: 0002_generation_timing_and_tokens
Revises: 0001_initial_schema
Create Date: 2026-10-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_generation_timing_and_tokens"
down_revision: str | Sequence[str] | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("learning_plans", sa.Column("token_usage", sa.JSON(), nullable=True))
    op.add_column("learning_plans", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("learning_plans", "started_at")
    op.drop_column("learning_plans", "token_usage")
