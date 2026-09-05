"""add PDF report config fields to app_settings

Revision ID: 0013
Revises: 0012
Create Date: 2026-09-05
"""
from alembic import op
import sqlalchemy as sa


revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "app_settings",
        sa.Column("report_title_prefix", sa.String(255), nullable=True),
    )
    op.add_column(
        "app_settings",
        sa.Column("cover_page_text", sa.Text(), nullable=True),
    )
    op.add_column(
        "app_settings",
        sa.Column("report_theme", sa.String(32), nullable=False, server_default="blue"),
    )
    op.add_column(
        "app_settings",
        sa.Column("include_cover_page_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("app_settings", "include_cover_page_default")
    op.drop_column("app_settings", "report_theme")
    op.drop_column("app_settings", "cover_page_text")
    op.drop_column("app_settings", "report_title_prefix")
