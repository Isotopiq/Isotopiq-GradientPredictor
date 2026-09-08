"""add compound_ids and compound_names to methods

Revision ID: 0015
Revises: 0014
Create Date: 2026-09-08
"""
from alembic import op
import sqlalchemy as sa

from app.models.jsonb_compat import JSONBCompat


revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "methods",
        sa.Column("compound_ids", JSONBCompat, nullable=True),
    )
    op.add_column(
        "methods",
        sa.Column("compound_names", JSONBCompat, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("methods", "compound_names")
    op.drop_column("methods", "compound_ids")
