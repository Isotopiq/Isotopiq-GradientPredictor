"""add dwell_volume_ml and dead_volume_ml to methods

Revision ID: 0011
Revises: 0010
Create Date: 2026-09-04
"""
from alembic import op
import sqlalchemy as sa


revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "methods",
        sa.Column("dwell_volume_ml", sa.Float, nullable=True),
    )
    op.add_column(
        "methods",
        sa.Column("dead_volume_ml", sa.Float, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("methods", "dead_volume_ml")
    op.drop_column("methods", "dwell_volume_ml")
