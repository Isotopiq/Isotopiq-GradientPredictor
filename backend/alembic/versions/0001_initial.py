"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-09-01
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "compounds",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("is_shared", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("name", sa.String(512), nullable=True),
        sa.Column("smiles", sa.Text, nullable=True),
        sa.Column("inchi", sa.Text, nullable=True),
        sa.Column("inchikey", sa.String(27), nullable=True),
        sa.Column("molfile", sa.Text, nullable=True),
        sa.Column("cas", sa.String(64), nullable=True),
        sa.Column("mw", sa.Float, nullable=True),
        sa.Column("logp", sa.Float, nullable=True),
        sa.Column("logd_at_ph", sa.Float, nullable=True),
        sa.Column("pka_values", postgresql.JSONB, nullable=True),
        sa.Column("tpsa", sa.Float, nullable=True),
        sa.Column("hbd", sa.Integer, nullable=True),
        sa.Column("hba", sa.Integer, nullable=True),
        sa.Column("rotatable_bonds", sa.Integer, nullable=True),
        sa.Column("aromatic_rings", sa.Integer, nullable=True),
        sa.Column("source", sa.String(32), nullable=False, server_default="manual"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_compounds_owner_id", "compounds", ["owner_id"])
    op.create_index("ix_compounds_inchikey", "compounds", ["inchikey"])
    op.create_index("ix_compounds_cas", "compounds", ["cas"])
    op.create_index("ix_compounds_name", "compounds", ["name"])

    op.create_table(
        "methods",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("column_type", sa.String(32), nullable=False),
        sa.Column("column_dims", postgresql.JSONB, nullable=True),
        sa.Column("mobile_phase_a", sa.String(255), nullable=True),
        sa.Column("mobile_phase_b", sa.String(255), nullable=True),
        sa.Column("additive", sa.String(255), nullable=True),
        sa.Column("ph", sa.Float, nullable=True),
        sa.Column("gradient_table", postgresql.JSONB, nullable=True),
        sa.Column("flow_rate_ml_min", sa.Float, nullable=True),
        sa.Column("temperature_c", sa.Float, nullable=True),
        sa.Column("method_signature", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_methods_owner_id", "methods", ["owner_id"])
    op.create_index("ix_methods_column_type", "methods", ["column_type"])
    op.create_index("ix_methods_method_signature", "methods", ["method_signature"])

    op.create_table(
        "runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("compound_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("compounds.id", ondelete="CASCADE"), nullable=False),
        sa.Column("method_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("methods.id", ondelete="CASCADE"), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("observed_rt_s", sa.Float, nullable=False),
        sa.Column("peak_width_s", sa.Float, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("run_date", sa.Date, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_runs_compound_id", "runs", ["compound_id"])
    op.create_index("ix_runs_method_id", "runs", ["method_id"])
    op.create_index("ix_runs_owner_id", "runs", ["owner_id"])

    op.create_table(
        "predictions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("compound_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("compounds.id", ondelete="CASCADE"), nullable=False),
        sa.Column("method_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("methods.id", ondelete="CASCADE"), nullable=False),
        sa.Column("predicted_rt_s", sa.Float, nullable=True),
        sa.Column("rt_lower_s", sa.Float, nullable=True),
        sa.Column("rt_upper_s", sa.Float, nullable=True),
        sa.Column("confidence", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("extrapolating", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("model_version", sa.String(64), nullable=False, server_default="rules-v1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_predictions_compound_id", "predictions", ["compound_id"])
    op.create_index("ix_predictions_method_id", "predictions", ["method_id"])

    op.create_table(
        "model_artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("column_type", sa.String(32), nullable=False),
        sa.Column("method_signature", sa.String(64), nullable=False),
        sa.Column("model_type", sa.String(32), nullable=False),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("artifact_path", sa.String(512), nullable=False),
        sa.Column("train_metrics", postgresql.JSONB, nullable=True),
        sa.Column("feature_schema", postgresql.JSONB, nullable=True),
        sa.Column("trained_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("n_samples", sa.Integer, nullable=False, server_default="0"),
    )
    op.create_index("ix_model_artifacts_owner_id", "model_artifacts", ["owner_id"])
    op.create_index("ix_model_artifacts_column_type", "model_artifacts", ["column_type"])
    op.create_index("ix_model_artifacts_method_signature", "model_artifacts", ["method_signature"])


def downgrade() -> None:
    op.drop_table("model_artifacts")
    op.drop_table("predictions")
    op.drop_table("runs")
    op.drop_table("methods")
    op.drop_table("compounds")
    op.drop_table("users")
