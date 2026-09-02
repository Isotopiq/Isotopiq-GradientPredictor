"""Fix model_artifacts.trained_at to use timezone-aware timestamp."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "model_artifacts",
        "trained_at",
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "model_artifacts",
        "trained_at",
        type_=sa.DateTime(),
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=False,
    )
