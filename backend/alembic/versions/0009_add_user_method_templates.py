"""add user method templates table

Revision ID: 0009
Revises: 0008_add_compound_lists
Create Date: 2026-09-02
"""
from alembic import op
import sqlalchemy as sa


revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_method_templates",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("category", sa.String(128), nullable=False, server_default="Custom"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("column_type", sa.String(32), nullable=False),
        sa.Column("mobile_phase_a", sa.String(255), nullable=True),
        sa.Column("mobile_phase_b", sa.String(255), nullable=True),
        sa.Column("additive", sa.String(255), nullable=True),
        sa.Column("ph", sa.Float, nullable=True),
        sa.Column("percent_b_start", sa.Float, nullable=False, server_default="5.0"),
        sa.Column("percent_b_end", sa.Float, nullable=False, server_default="95.0"),
        sa.Column("gradient_time_min", sa.Float, nullable=False, server_default="20.0"),
        sa.Column("flow_rate_ml_min", sa.Float, nullable=False, server_default="0.4"),
        sa.Column("temperature_c", sa.Float, nullable=False, server_default="30.0"),
        sa.Column("column_length_mm", sa.Integer, nullable=False, server_default="100"),
        sa.Column("particle_size_um", sa.Float, nullable=False, server_default="1.8"),
        sa.Column("is_shared", sa.Boolean, nullable=False, server_default=sa.sql.expression.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("user_method_templates")
