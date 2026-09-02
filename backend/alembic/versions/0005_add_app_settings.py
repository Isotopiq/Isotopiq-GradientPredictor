"""Add app settings table for admin-configurable branding and logo."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app_settings",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("lab_name", sa.String(255), nullable=False, server_default="IsotopiQ"),
        sa.Column("lab_subtitle", sa.String(255), nullable=False, server_default="LC-MS Method Prediction Suite"),
        sa.Column("lab_address", sa.Text(), nullable=True),
        sa.Column("lab_website", sa.String(255), nullable=True),
        sa.Column("logo_bytes", sa.LargeBinary(), nullable=True),
        sa.Column("logo_mime_type", sa.String(50), nullable=True),
        sa.Column(
            "report_footer",
            sa.Text(),
            nullable=False,
            server_default="Predictions are estimates derived from physicochemical heuristics and statistical models. "
                           "They require experimental verification before use in regulated or production analytical work.",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("app_settings")
