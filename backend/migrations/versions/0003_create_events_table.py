"""create events table

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-21 00:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("severity", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("source_name", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_events_timestamp", "events", ["timestamp"])
    op.create_index("ix_events_severity", "events", ["severity"])
    op.create_index("ix_events_category", "events", ["category"])
    op.create_index("ix_events_source_type", "events", ["source_type"])
    op.create_index("ix_events_source_id", "events", ["source_id"])


def downgrade() -> None:
    op.drop_index("ix_events_source_id", table_name="events")
    op.drop_index("ix_events_source_type", table_name="events")
    op.drop_index("ix_events_category", table_name="events")
    op.drop_index("ix_events_severity", table_name="events")
    op.drop_index("ix_events_timestamp", table_name="events")
    op.drop_table("events")
