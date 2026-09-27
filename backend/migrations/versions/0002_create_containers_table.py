"""create containers table

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-21 00:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "containers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("host_id", sa.Integer(), sa.ForeignKey("hosts.id"), nullable=False),
        sa.Column("container_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("image", sa.String(), nullable=False),
        sa.Column("image_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("health_status", sa.String(), nullable=True),
        sa.Column("restart_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("is_present", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("first_seen_at", sa.DateTime(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_containers_host_id", "containers", ["host_id"])
    op.create_index("ix_containers_container_id", "containers", ["container_id"], unique=True)
    op.create_index("ix_containers_name", "containers", ["name"])
    op.create_index("ix_containers_state", "containers", ["state"])
    op.create_index("ix_containers_is_present", "containers", ["is_present"])


def downgrade() -> None:
    op.drop_index("ix_containers_is_present", table_name="containers")
    op.drop_index("ix_containers_state", table_name="containers")
    op.drop_index("ix_containers_name", table_name="containers")
    op.drop_index("ix_containers_container_id", table_name="containers")
    op.drop_index("ix_containers_host_id", table_name="containers")
    op.drop_table("containers")
