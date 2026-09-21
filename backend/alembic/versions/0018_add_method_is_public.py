"""add is_public visibility flag to methods

Existing rows are backfilled to is_public=True: methods were already
visible to every authenticated user in the library list, so preserving
that exposure is less surprising than suddenly hiding them.

Revision ID: 0018
Revises: 0017
Create Date: 2026-09-20
"""
import sqlalchemy as sa

from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "methods",
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    # Backfill: existing methods were already listed to all users
    op.execute("UPDATE methods SET is_public = true")


def downgrade() -> None:
    op.drop_column("methods", "is_public")
