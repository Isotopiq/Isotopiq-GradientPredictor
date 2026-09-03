"""add compounds_smiles to methods

Revision ID: 0010
Revises: 0009
Create Date: 2026-09-03
"""
from alembic import op
import sqlalchemy as sa

from app.models.jsonb_compat import JSONBCompat


revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "methods",
        sa.Column("compounds_smiles", JSONBCompat, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("methods", "compounds_smiles")
