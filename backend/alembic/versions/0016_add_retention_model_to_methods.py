"""add retention model fields to methods

Revision ID: 0016
Revises: 0015
Create Date: 2026-09-08
"""
from alembic import op
import sqlalchemy as sa


revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("methods", sa.Column("retention_model", sa.String(32), nullable=True))
    op.add_column("methods", sa.Column("retention_model_label", sa.String(255), nullable=True))
    op.add_column("methods", sa.Column("retention_model_equation", sa.String(512), nullable=True))
    op.add_column("methods", sa.Column("retention_model_reference", sa.String(512), nullable=True))
    op.add_column("methods", sa.Column("retention_model_rationale", sa.String(512), nullable=True))


def downgrade() -> None:
    op.drop_column("methods", "retention_model_rationale")
    op.drop_column("methods", "retention_model_reference")
    op.drop_column("methods", "retention_model_equation")
    op.drop_column("methods", "retention_model_label")
    op.drop_column("methods", "retention_model")
