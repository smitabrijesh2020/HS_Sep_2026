"""SQLAlchemy ORM models - target persistence schema.

NOTE ON VERIFICATION STATUS: this file was authored against SQLAlchemy 2.0
declarative-mapping syntax but could NOT be executed in this Cowork sandbox
(no outbound network access to install `sqlalchemy`/`alembic`). Treat this
module as "implemented but not externally verified" until run through
`pip install -e .[dev]` and `pytest tests/integration` in an environment
with package-index access. The runnable, verified vertical slice for this
session uses `repositories/sqlite_repository.py` (stdlib `sqlite3` only),
which mirrors this same schema.

Design notes:
  * UUID (string) primary keys throughout - no sequential IDs exposed.
  * created_at/created_by/updated_at/updated_by on every mutable table.
  * is_archived boolean for soft deletion where business records must be
    retained (programs, batches, nominations) rather than hard-deleted.
  * Unique constraint on (employee_id, program_id, batch_id) is NOT placed
    at the DB level as a blanket unique index, because withdrawn/completed
    historical nominations must be retained alongside a new active one.
    Duplicate-*active*-nomination prevention is enforced in
    services/nomination_service.py at write time, backed by a partial
    unique index in Postgres (see migration) / application-level check in
    SQLite.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _uuid_col():
    from domain.models import new_id

    return mapped_column(String(36), primary_key=True, default=new_id)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False, default="system")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    updated_by: Mapped[str] = mapped_column(String(255), nullable=False, default="system")


class User(Base, TimestampMixin):
    __tablename__ = "users"
    id: Mapped[str] = _uuid_col()
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Role(Base):
    __tablename__ = "roles"
    id: Mapped[str] = _uuid_col()
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")


class Program(Base, TimestampMixin):
    __tablename__ = "programs"
    id: Mapped[str] = _uuid_col()
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    owner: Mapped[str] = mapped_column(String(255), default="")
    business_unit: Mapped[str] = mapped_column(String(255), default="")
    technology: Mapped[str] = mapped_column(String(255), default="")
    prerequisites: Mapped[str] = mapped_column(Text, default="")
    nomination_open_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    nomination_close_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    delivery_start_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    delivery_end_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="Draft")
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    batches: Mapped[list["Batch"]] = relationship(back_populates="program")

    __table_args__ = (
        CheckConstraint(
            "status in ('Draft','Active','Closed','Archived')", name="ck_program_status"
        ),
    )


class Batch(Base, TimestampMixin):
    __tablename__ = "batches"
    id: Mapped[str] = _uuid_col()
    program_id: Mapped[str] = mapped_column(ForeignKey("programs.id"), nullable=False)
    trf_number: Mapped[str] = mapped_column(String(100), nullable=False)
    start_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    capacity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    trainer: Mapped[str] = mapped_column(String(255), default="")
    location: Mapped[str] = mapped_column(String(255), default="")
    delivery_mode: Mapped[str] = mapped_column(String(50), default="Virtual")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="Planned")
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    program: Mapped["Program"] = relationship(back_populates="batches")

    __table_args__ = (
        UniqueConstraint("program_id", "trf_number", name="uq_batch_program_trf"),
        CheckConstraint("capacity >= 0", name="ck_batch_capacity_nonneg"),
    )


class Employee(Base, TimestampMixin):
    __tablename__ = "employees"
    id: Mapped[str] = _uuid_col()
    employee_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    manager_email: Mapped[str] = mapped_column(String(320), default="")
    grade: Mapped[str] = mapped_column(String(20), default="")
    location: Mapped[str] = mapped_column(String(255), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Nomination(Base, TimestampMixin):
    __tablename__ = "nominations"
    id: Mapped[str] = _uuid_col()
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.id"), nullable=False)
    program_id: Mapped[str] = mapped_column(ForeignKey("programs.id"), nullable=False)
    batch_id: Mapped[str] = mapped_column(ForeignKey("batches.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="Draft")
    source: Mapped[str] = mapped_column(String(20), default="Manual")
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "status in ('Draft','Submitted','PendingValidation','Eligible','Rejected',"
            "'Waitlisted','Confirmed','Withdrawn','Completed')",
            name="ck_nomination_status",
        ),
        # Postgres only: a partial unique index enforcing "one active nomination per
        # (employee, program, batch)" belongs in the migration as raw DDL, since
        # SQLAlchemy's UniqueConstraint cannot express a WHERE clause portably.
    )


class EligibilityRuleResult(Base):
    __tablename__ = "eligibility_results"
    id: Mapped[str] = _uuid_col()
    nomination_id: Mapped[str] = mapped_column(ForeignKey("nominations.id"), nullable=False)
    rule_source: Mapped[str] = mapped_column(String(50), nullable=False)
    rule_name: Mapped[str] = mapped_column(String(255), nullable=False)
    result: Mapped[str] = mapped_column(String(30), nullable=False)
    detail: Mapped[str] = mapped_column(Text, default="")
    evaluated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_manual_override: Mapped[bool] = mapped_column(Boolean, default=False)
    override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    override_actor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    override_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "result in ('Pass','Fail','Pending','NotApplicable','DataUnavailable')",
            name="ck_rule_result",
        ),
    )


class CommunicationLog(Base):
    __tablename__ = "communication_log"
    id: Mapped[str] = _uuid_col()
    nomination_id: Mapped[str] = mapped_column(ForeignKey("nominations.id"), nullable=False)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.id"), nullable=False)
    comm_type: Mapped[str] = mapped_column(String(30), nullable=False)
    template_version: Mapped[str] = mapped_column(String(20), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="Pending")
    graph_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("idempotency_key", "status", name="uq_comm_idempotency_status"),
    )


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[str] = _uuid_col()
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    actor: Mapped[str] = mapped_column(String(255), nullable=False, default="system")
    detail: Mapped[str] = mapped_column(Text, default="")
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
