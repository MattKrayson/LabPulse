"""add last_error column to containers

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-27 00:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("containers", sa.Column("last_error", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("containers", "last_error")
