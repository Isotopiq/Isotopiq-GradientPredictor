"""add favicon fields to app_settings

Revision ID: 0014
Revises: 0013
Create Date: 2026-09-05
"""
from alembic import op
import sqlalchemy as sa


revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "app_settings",
        sa.Column("favicon_bytes", sa.LargeBinary(), nullable=True),
    )
    op.add_column(
        "app_settings",
        sa.Column("favicon_mime_type", sa.String(50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("app_settings", "favicon_mime_type")
    op.drop_column("app_settings", "favicon_bytes")
