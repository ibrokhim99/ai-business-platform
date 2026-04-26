"""Initial schema — users, prediction_logs, model_versions, business_profiles, credit_applications

Revision ID: 0001
Revises:
Create Date: 2026-04-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── users ──────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False, server_default="customer"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # ── prediction_logs ────────────────────────────────────────────────────────
    op.create_table(
        "prediction_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("model_id", sa.String(20), nullable=False),
        sa.Column("model_version", sa.String(50), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("user_role", sa.String(50), nullable=True),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column("input_snapshot", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("output_snapshot", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_stub", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("cache_hit", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("request_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_prediction_logs"),
    )
    op.create_index("ix_prediction_logs_model_id", "prediction_logs", ["model_id"])
    op.create_index("ix_prediction_logs_input_hash", "prediction_logs", ["input_hash"])

    # ── model_versions ─────────────────────────────────────────────────────────
    op.create_table(
        "model_versions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("model_id", sa.String(20), nullable=False),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("mlflow_run_id", sa.String(100), nullable=True),
        sa.Column("artifact_uri", sa.Text(), nullable=True),
        sa.Column("metrics", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("params", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("is_stub", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_production", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("trained_by", sa.String(255), nullable=True),
        sa.Column("dataset_ref", sa.Text(), nullable=True),
        sa.Column("trained_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_model_versions"),
    )
    op.create_index("ix_model_versions_model_id", "model_versions", ["model_id"])
    op.create_index("ix_model_versions_is_production", "model_versions", ["is_production"])

    # ── business_profiles ──────────────────────────────────────────────────────
    op.create_table(
        "business_profiles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("customer_id", sa.String(100), nullable=False),
        sa.Column("mcc_code", sa.String(10), nullable=False),
        sa.Column("niche_label", sa.String(255), nullable=True),
        sa.Column("region_id", sa.String(100), nullable=True),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lon", sa.Float(), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("monthly_revenue", sa.Float(), nullable=True),
        sa.Column("employee_count", sa.Integer(), nullable=True),
        sa.Column("registration_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("extra_features", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_business_profiles"),
    )
    op.create_index("ix_business_profiles_customer_id", "business_profiles", ["customer_id"])
    op.create_index("ix_business_profiles_mcc_code", "business_profiles", ["mcc_code"])

    # ── credit_applications ────────────────────────────────────────────────────
    op.create_table(
        "credit_applications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("customer_id", sa.String(100), nullable=False),
        sa.Column("business_profile_id", sa.Integer(), nullable=True),
        sa.Column("requested_amount", sa.Float(), nullable=False),
        sa.Column("loan_term_months", sa.Integer(), nullable=False, server_default="36"),
        sa.Column("purpose", sa.String(255), nullable=True),
        sa.Column("credit_score", sa.Float(), nullable=True),
        sa.Column("risk_grade", sa.String(10), nullable=True),
        sa.Column("decision", sa.String(50), nullable=True),
        sa.Column("officer_id", sa.Integer(), nullable=True),
        sa.Column("model_outputs", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_credit_applications"),
    )
    op.create_index("ix_credit_applications_customer_id", "credit_applications", ["customer_id"])


def downgrade() -> None:
    op.drop_table("credit_applications")
    op.drop_table("business_profiles")
    op.drop_table("model_versions")
    op.drop_table("prediction_logs")
    op.drop_table("users")
