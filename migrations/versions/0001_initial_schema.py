"""Initial schema: users, roles, programs, batches, employees, nominations,
eligibility_results, communication_log, audit_log.

NOTE: written to Alembic 1.13 op.* conventions but not executed in this
session (no network access to install alembic in the Cowork sandbox).
Review and run `alembic upgrade head` in a real environment before relying
on it.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-09-01
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
        sa.Column("updated_by", sa.String(255), nullable=False),
    )

    op.create_table(
        "roles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("description", sa.Text, server_default=""),
    )

    op.create_table(
        "programs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, server_default=""),
        sa.Column("owner", sa.String(255), server_default=""),
        sa.Column("business_unit", sa.String(255), server_default=""),
        sa.Column("technology", sa.String(255), server_default=""),
        sa.Column("prerequisites", sa.Text, server_default=""),
        sa.Column("nomination_open_date", sa.DateTime, nullable=True),
        sa.Column("nomination_close_date", sa.DateTime, nullable=True),
        sa.Column("delivery_start_date", sa.DateTime, nullable=True),
        sa.Column("delivery_end_date", sa.DateTime, nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="Draft"),
        sa.Column("is_archived", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
        sa.Column("updated_by", sa.String(255), nullable=False),
        sa.CheckConstraint("status in ('Draft','Active','Closed','Archived')", name="ck_program_status"),
    )

    op.create_table(
        "batches",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("program_id", sa.String(36), sa.ForeignKey("programs.id"), nullable=False),
        sa.Column("trf_number", sa.String(100), nullable=False),
        sa.Column("start_date", sa.DateTime, nullable=True),
        sa.Column("end_date", sa.DateTime, nullable=True),
        sa.Column("capacity", sa.Integer, nullable=False, server_default="0"),
        sa.Column("trainer", sa.String(255), server_default=""),
        sa.Column("location", sa.String(255), server_default=""),
        sa.Column("delivery_mode", sa.String(50), server_default="Virtual"),
        sa.Column("status", sa.String(50), nullable=False, server_default="Planned"),
        sa.Column("is_archived", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
        sa.Column("updated_by", sa.String(255), nullable=False),
        sa.UniqueConstraint("program_id", "trf_number", name="uq_batch_program_trf"),
        sa.CheckConstraint("capacity >= 0", name="ck_batch_capacity_nonneg"),
    )

    op.create_table(
        "employees",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("employee_code", sa.String(50), nullable=False, unique=True),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("manager_email", sa.String(320), server_default=""),
        sa.Column("grade", sa.String(20), server_default=""),
        sa.Column("location", sa.String(255), server_default=""),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
        sa.Column("updated_by", sa.String(255), nullable=False),
    )

    op.create_table(
        "nominations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("employee_id", sa.String(36), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("program_id", sa.String(36), sa.ForeignKey("programs.id"), nullable=False),
        sa.Column("batch_id", sa.String(36), sa.ForeignKey("batches.id"), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="Draft"),
        sa.Column("source", sa.String(20), server_default="Manual"),
        sa.Column("is_archived", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
        sa.Column("updated_by", sa.String(255), nullable=False),
        sa.CheckConstraint(
            "status in ('Draft','Submitted','PendingValidation','Eligible','Rejected',"
            "'Waitlisted','Confirmed','Withdrawn','Completed')",
            name="ck_nomination_status",
        ),
    )
    op.create_index("ix_nominations_employee", "nominations", ["employee_id"])
    op.create_index("ix_nominations_batch", "nominations", ["batch_id"])

    # Postgres-only partial unique index: one ACTIVE nomination per
    # (employee, program, batch). Guarded because SQLite's dialect used in
    # dev/test does not support this DDL the same way; apply conditionally
    # in a real Postgres target.
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            """
            CREATE UNIQUE INDEX uq_active_nomination
            ON nominations (employee_id, program_id, batch_id)
            WHERE status IN ('Draft','Submitted','PendingValidation','Eligible','Waitlisted','Confirmed')
              AND is_archived = false;
            """
        )

    op.create_table(
        "eligibility_results",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("nomination_id", sa.String(36), sa.ForeignKey("nominations.id"), nullable=False),
        sa.Column("rule_source", sa.String(50), nullable=False),
        sa.Column("rule_name", sa.String(255), nullable=False),
        sa.Column("result", sa.String(30), nullable=False),
        sa.Column("detail", sa.Text, server_default=""),
        sa.Column("evaluated_at", sa.DateTime, nullable=False),
        sa.Column("is_manual_override", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("override_reason", sa.Text, nullable=True),
        sa.Column("override_actor", sa.String(255), nullable=True),
        sa.Column("override_at", sa.DateTime, nullable=True),
        sa.CheckConstraint(
            "result in ('Pass','Fail','Pending','NotApplicable','DataUnavailable')",
            name="ck_rule_result",
        ),
    )
    op.create_index("ix_eligibility_nomination", "eligibility_results", ["nomination_id"])

    op.create_table(
        "communication_log",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("nomination_id", sa.String(36), sa.ForeignKey("nominations.id"), nullable=False),
        sa.Column("employee_id", sa.String(36), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("comm_type", sa.String(30), nullable=False),
        sa.Column("template_version", sa.String(20), nullable=False),
        sa.Column("idempotency_key", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="Pending"),
        sa.Column("graph_message_id", sa.String(255), nullable=True),
        sa.Column("retry_count", sa.Integer, server_default="0"),
        sa.Column("error_detail", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("sent_at", sa.DateTime, nullable=True),
        sa.UniqueConstraint("idempotency_key", "status", name="uq_comm_idempotency_status"),
    )
    op.create_index("ix_comm_idempotency", "communication_log", ["idempotency_key"])

    op.create_table(
        "audit_log",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.String(36), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("actor", sa.String(255), nullable=False, server_default="system"),
        sa.Column("detail", sa.Text, server_default=""),
        sa.Column("occurred_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_audit_entity", "audit_log", ["entity_type", "entity_id"])


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("communication_log")
    op.drop_table("eligibility_results")
    op.drop_table("nominations")
    op.drop_table("employees")
    op.drop_table("batches")
    op.drop_table("programs")
    op.drop_table("roles")
    op.drop_table("users")
