"""create webhooks table

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-27 00:05:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "webhooks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("format", sa.String(), nullable=False, server_default="generic"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("notify_on_open", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("notify_on_resolve", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_triggered_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("webhooks")
