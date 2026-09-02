"""Add method sharing fields.

Revision ID: 0003
Revises: 0002_add_is_admin
Create Date: 2024-01-01
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("methods", sa.Column("is_shared", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("methods", sa.Column("share_token", sa.String(64), nullable=True))
    op.create_index("ix_methods_share_token", "methods", ["share_token"])


def downgrade() -> None:
    op.drop_index("ix_methods_share_token", table_name="methods")
    op.drop_column("methods", "share_token")
    op.drop_column("methods", "is_shared")
