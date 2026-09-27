"""add tls certificate fields to hosts

Revision ID: 0010
Revises: 0009
Create Date: 2026-09-27 00:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("hosts", sa.Column("tls_ca_cert", sa.Text(), nullable=True))
    op.add_column("hosts", sa.Column("tls_client_cert", sa.Text(), nullable=True))
    op.add_column("hosts", sa.Column("tls_client_key", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("hosts", "tls_client_key")
    op.drop_column("hosts", "tls_client_cert")
    op.drop_column("hosts", "tls_ca_cert")
