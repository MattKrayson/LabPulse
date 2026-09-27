"""create metrics table

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-21 00:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "metrics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("container_id", sa.String(), nullable=False),
        sa.Column("metric_type", sa.String(), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_metrics_timestamp", "metrics", ["timestamp"])
    op.create_index("ix_metrics_container_id", "metrics", ["container_id"])
    op.create_index("ix_metrics_metric_type", "metrics", ["metric_type"])
    op.create_index(
        "ix_metrics_container_type_timestamp",
        "metrics",
        ["container_id", "metric_type", "timestamp"],
    )


def downgrade() -> None:
    op.drop_index("ix_metrics_container_type_timestamp", table_name="metrics")
    op.drop_index("ix_metrics_metric_type", table_name="metrics")
    op.drop_index("ix_metrics_container_id", table_name="metrics")
    op.drop_index("ix_metrics_timestamp", table_name="metrics")
    op.drop_table("metrics")
