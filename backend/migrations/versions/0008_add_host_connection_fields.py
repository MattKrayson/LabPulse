"""add remote connection fields to hosts

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-27 00:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("hosts", sa.Column("connection_url", sa.String(), nullable=True))
    op.add_column("hosts", sa.Column("status", sa.String(), nullable=False, server_default="unknown"))
    op.add_column("hosts", sa.Column("last_error", sa.String(), nullable=True))
    op.add_column("hosts", sa.Column("last_checked_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("hosts", "last_checked_at")
    op.drop_column("hosts", "last_error")
    op.drop_column("hosts", "status")
    op.drop_column("hosts", "connection_url")
