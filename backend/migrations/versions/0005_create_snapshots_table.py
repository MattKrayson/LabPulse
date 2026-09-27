"""create snapshots table

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-21 00:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("container_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("image", sa.String(), nullable=False),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("health_status", sa.String(), nullable=True),
        sa.Column("restart_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_snapshots_timestamp", "snapshots", ["timestamp"])
    op.create_index("ix_snapshots_container_id", "snapshots", ["container_id"])
    op.create_index(
        "ix_snapshots_container_timestamp",
        "snapshots",
        ["container_id", "timestamp"],
    )


def downgrade() -> None:
    op.drop_index("ix_snapshots_container_timestamp", table_name="snapshots")
    op.drop_index("ix_snapshots_container_id", table_name="snapshots")
    op.drop_index("ix_snapshots_timestamp", table_name="snapshots")
    op.drop_table("snapshots")
