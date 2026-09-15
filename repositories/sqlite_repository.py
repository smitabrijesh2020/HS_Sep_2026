"""Runnable MVP persistence layer using stdlib `sqlite3` only.

Why this exists alongside `orm_models.py`: this Cowork sandbox has no
outbound network access, so SQLAlchemy/Alembic could not be pip-installed
or exercised here. To give an honestly *verified* end-to-end slice
(Program -> Batch -> Nomination -> Eligibility -> Dry-run Communication Log)
this module implements the same schema directly with parameterized SQL via
`sqlite3`, which ships with the Python standard library.

This is documented as the MVP/demo persistence path. `orm_models.py` +
Alembic remain the target production schema for PostgreSQL once dependency
installation is available.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Iterator

from domain.models import (
    AuditLogEntry,
    Batch,
    CommunicationLogEntry,
    EligibilityDecision,
    EligibilityRuleResult,
    Employee,
    Nomination,
    Program,
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS programs (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    owner TEXT DEFAULT '',
    business_unit TEXT DEFAULT '',
    technology TEXT DEFAULT '',
    prerequisites TEXT DEFAULT '',
    nomination_open_date TEXT,
    nomination_close_date TEXT,
    delivery_start_date TEXT,
    delivery_end_date TEXT,
    status TEXT NOT NULL DEFAULT 'Draft'
        CHECK (status IN ('Draft','Active','Closed','Archived')),
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    updated_by TEXT NOT NULL,
    is_archived INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS batches (
    id TEXT PRIMARY KEY,
    program_id TEXT NOT NULL REFERENCES programs(id),
    trf_number TEXT NOT NULL,
    start_date TEXT,
    end_date TEXT,
    capacity INTEGER NOT NULL DEFAULT 0 CHECK (capacity >= 0),
    trainer TEXT DEFAULT '',
    location TEXT DEFAULT '',
    delivery_mode TEXT DEFAULT 'Virtual',
    status TEXT NOT NULL DEFAULT 'Planned',
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    updated_by TEXT NOT NULL,
    is_archived INTEGER NOT NULL DEFAULT 0,
    UNIQUE (program_id, trf_number)
);

CREATE TABLE IF NOT EXISTS employees (
    id TEXT PRIMARY KEY,
    employee_code TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    email TEXT NOT NULL,
    manager_email TEXT DEFAULT '',
    grade TEXT DEFAULT '',
    location TEXT DEFAULT '',
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS nominations (
    id TEXT PRIMARY KEY,
    employee_id TEXT NOT NULL REFERENCES employees(id),
    program_id TEXT NOT NULL REFERENCES programs(id),
    batch_id TEXT NOT NULL REFERENCES batches(id),
    status TEXT NOT NULL DEFAULT 'Draft'
        CHECK (status IN ('Draft','Submitted','PendingValidation','Eligible','Rejected',
                           'Waitlisted','Confirmed','Withdrawn','Completed')),
    source TEXT DEFAULT 'Manual',
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    updated_by TEXT NOT NULL,
    is_archived INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_nominations_employee ON nominations(employee_id);
CREATE INDEX IF NOT EXISTS ix_nominations_batch ON nominations(batch_id);

CREATE TABLE IF NOT EXISTS eligibility_results (
    id TEXT PRIMARY KEY,
    nomination_id TEXT NOT NULL REFERENCES nominations(id),
    rule_source TEXT NOT NULL,
    rule_name TEXT NOT NULL,
    result TEXT NOT NULL CHECK (result IN ('Pass','Fail','Pending','NotApplicable','DataUnavailable')),
    detail TEXT DEFAULT '',
    evaluated_at TEXT NOT NULL,
    is_manual_override INTEGER NOT NULL DEFAULT 0,
    override_reason TEXT,
    override_actor TEXT,
    override_at TEXT
);
CREATE INDEX IF NOT EXISTS ix_eligibility_nomination ON eligibility_results(nomination_id);

CREATE TABLE IF NOT EXISTS eligibility_decisions (
    id TEXT PRIMARY KEY,
    nomination_id TEXT NOT NULL REFERENCES nominations(id),
    status TEXT NOT NULL,
    reasons TEXT DEFAULT '',
    decided_at TEXT NOT NULL,
    decided_by TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS communication_log (
    id TEXT PRIMARY KEY,
    nomination_id TEXT NOT NULL REFERENCES nominations(id),
    employee_id TEXT NOT NULL REFERENCES employees(id),
    comm_type TEXT NOT NULL,
    template_version TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Pending',
    graph_message_id TEXT,
    retry_count INTEGER DEFAULT 0,
    error_detail TEXT,
    created_at TEXT NOT NULL,
    sent_at TEXT
);
CREATE INDEX IF NOT EXISTS ix_comm_idempotency ON communication_log(idempotency_key);

CREATE TABLE IF NOT EXISTS audit_log (
    id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    action TEXT NOT NULL,
    actor TEXT NOT NULL DEFAULT 'system',
    detail TEXT DEFAULT '',
    occurred_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_audit_entity ON audit_log(entity_type, entity_id);
"""


def _dt(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return value.isoformat()


class SqliteRepository:
    """Thin, parameterized-SQL repository for the vertical slice.

    All statements use `?` placeholders (never string interpolation) to
    prevent SQL injection, per the engineering requirements.
    """

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        self._init_schema()

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._conn() as conn:
            conn.executescript(SCHEMA)

    # ---- Programs ----------------------------------------------------
    def add_program(self, program: Program) -> None:
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO programs (id, name, description, owner, business_unit, technology,
                    prerequisites, nomination_open_date, nomination_close_date, delivery_start_date,
                    delivery_end_date, status, created_at, created_by, updated_at, updated_by, is_archived)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    program.id, program.name, program.description, program.owner,
                    program.business_unit, program.technology, program.prerequisites,
                    _dt(program.nomination_open_date), _dt(program.nomination_close_date),
                    _dt(program.delivery_start_date), _dt(program.delivery_end_date),
                    program.status.value, _dt(program.created_at), program.created_by,
                    _dt(program.updated_at), program.updated_by, int(program.is_archived),
                ),
            )

    def list_programs(self) -> list[sqlite3.Row]:
        with self._conn() as conn:
            return conn.execute("SELECT * FROM programs WHERE is_archived = 0").fetchall()

    # ---- Batches -------------------------------------------------------
    def add_batch(self, batch: Batch) -> None:
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO batches (id, program_id, trf_number, start_date, end_date, capacity,
                    trainer, location, delivery_mode, status, created_at, created_by, updated_at,
                    updated_by, is_archived)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    batch.id, batch.program_id, batch.trf_number, _dt(batch.start_date),
                    _dt(batch.end_date), batch.capacity, batch.trainer, batch.location,
                    batch.delivery_mode, batch.status.value, _dt(batch.created_at),
                    batch.created_by, _dt(batch.updated_at), batch.updated_by, int(batch.is_archived),
                ),
            )

    def list_batches(self, program_id: str | None = None) -> list[sqlite3.Row]:
        with self._conn() as conn:
            if program_id:
                return conn.execute(
                    "SELECT * FROM batches WHERE program_id = ? AND is_archived = 0", (program_id,)
                ).fetchall()
            return conn.execute("SELECT * FROM batches WHERE is_archived = 0").fetchall()

    def seat_summary(self, batch_id: str) -> dict:
        with self._conn() as conn:
            cap_row = conn.execute("SELECT capacity FROM batches WHERE id = ?", (batch_id,)).fetchone()
            capacity = cap_row["capacity"] if cap_row else 0
            filled = conn.execute(
                """SELECT COUNT(*) c FROM nominations WHERE batch_id = ? AND is_archived = 0
                   AND status IN ('Submitted','PendingValidation','Eligible','Confirmed')""",
                (batch_id,),
            ).fetchone()["c"]
            waitlisted = conn.execute(
                "SELECT COUNT(*) c FROM nominations WHERE batch_id = ? AND status = 'Waitlisted' AND is_archived = 0",
                (batch_id,),
            ).fetchone()["c"]
            available = max(capacity - filled, 0)
            utilization = round(filled / capacity, 4) if capacity else 0.0
            return {
                "capacity": capacity, "filled": filled, "available": available,
                "waitlisted": waitlisted, "utilization": utilization,
            }

    # ---- Employees -----------------------------------------------------
    def add_employee(self, employee: Employee) -> None:
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO employees (id, employee_code, display_name, email, manager_email,
                    grade, location, is_active) VALUES (?,?,?,?,?,?,?,?)""",
                (
                    employee.id, employee.employee_code, employee.display_name, employee.email,
                    employee.manager_email, employee.grade, employee.location, int(employee.is_active),
                ),
            )

    def list_employees(self) -> list[sqlite3.Row]:
        with self._conn() as conn:
            return conn.execute("SELECT * FROM employees").fetchall()

    # ---- Nominations -----------------------------------------------------
    def list_nominations(self, employee_id: str | None = None) -> list[Nomination]:
        with self._conn() as conn:
            if employee_id:
                rows = conn.execute(
                    "SELECT * FROM nominations WHERE employee_id = ?", (employee_id,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM nominations").fetchall()
        return [self._row_to_nomination(r) for r in rows]

    @staticmethod
    def _row_to_nomination(row: sqlite3.Row) -> Nomination:
        from domain.enums import NominationStatus

        return Nomination(
            id=row["id"], employee_id=row["employee_id"], program_id=row["program_id"],
            batch_id=row["batch_id"], status=NominationStatus(row["status"]), source=row["source"],
            created_at=datetime.fromisoformat(row["created_at"]), created_by=row["created_by"],
            updated_at=datetime.fromisoformat(row["updated_at"]), updated_by=row["updated_by"],
            is_archived=bool(row["is_archived"]),
        )

    def add_nomination(self, nomination: Nomination) -> None:
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO nominations (id, employee_id, program_id, batch_id, status, source,
                    created_at, created_by, updated_at, updated_by, is_archived)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    nomination.id, nomination.employee_id, nomination.program_id, nomination.batch_id,
                    nomination.status.value, nomination.source, _dt(nomination.created_at),
                    nomination.created_by, _dt(nomination.updated_at), nomination.updated_by,
                    int(nomination.is_archived),
                ),
            )

    def update_nomination_status(self, nomination_id: str, status: str, actor: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE nominations SET status = ?, updated_at = ?, updated_by = ? WHERE id = ?",
                (status, datetime.utcnow().isoformat(), actor, nomination_id),
            )

    # ---- Eligibility -----------------------------------------------------
    def add_eligibility_results(self, results: list[EligibilityRuleResult]) -> None:
        with self._conn() as conn:
            for r in results:
                conn.execute(
                    """INSERT INTO eligibility_results (id, nomination_id, rule_source, rule_name,
                        result, detail, evaluated_at, is_manual_override, override_reason,
                        override_actor, override_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        r.id, r.nomination_id, r.rule_source, r.rule_name, r.result.value, r.detail,
                        _dt(r.evaluated_at), int(r.is_manual_override), r.override_reason,
                        r.override_actor, _dt(r.override_at),
                    ),
                )

    def add_eligibility_decision(self, decision: EligibilityDecision) -> None:
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO eligibility_decisions (id, nomination_id, status, reasons,
                    decided_at, decided_by) VALUES (?,?,?,?,?,?)""",
                (
                    decision.id, decision.nomination_id, decision.status.value,
                    " | ".join(decision.reasons), _dt(decision.decided_at), decision.decided_by,
                ),
            )

    def list_eligibility_results(self, nomination_id: str) -> list[sqlite3.Row]:
        with self._conn() as conn:
            return conn.execute(
                "SELECT * FROM eligibility_results WHERE nomination_id = ?", (nomination_id,)
            ).fetchall()

    # ---- Communication log ------------------------------------------------
    def list_communication_log(self, nomination_id: str | None = None) -> list[CommunicationLogEntry]:
        with self._conn() as conn:
            if nomination_id:
                rows = conn.execute(
                    "SELECT * FROM communication_log WHERE nomination_id = ?", (nomination_id,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM communication_log").fetchall()
        return [self._row_to_comm(r) for r in rows]

    @staticmethod
    def _row_to_comm(row: sqlite3.Row) -> CommunicationLogEntry:
        from domain.enums import CommunicationStatus, CommunicationType

        return CommunicationLogEntry(
            id=row["id"], nomination_id=row["nomination_id"], employee_id=row["employee_id"],
            comm_type=CommunicationType(row["comm_type"]), template_version=row["template_version"],
            idempotency_key=row["idempotency_key"], status=CommunicationStatus(row["status"]),
            graph_message_id=row["graph_message_id"], retry_count=row["retry_count"] or 0,
            error_detail=row["error_detail"],
            created_at=datetime.fromisoformat(row["created_at"]),
            sent_at=datetime.fromisoformat(row["sent_at"]) if row["sent_at"] else None,
        )

    def add_communication_log(self, entry: CommunicationLogEntry) -> None:
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO communication_log (id, nomination_id, employee_id, comm_type,
                    template_version, idempotency_key, status, graph_message_id, retry_count,
                    error_detail, created_at, sent_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    entry.id, entry.nomination_id, entry.employee_id, entry.comm_type.value,
                    entry.template_version, entry.idempotency_key, entry.status.value,
                    entry.graph_message_id, entry.retry_count, entry.error_detail,
                    _dt(entry.created_at), _dt(entry.sent_at),
                ),
            )

    # ---- Audit -------------------------------------------------------------
    def add_audit(self, entry: AuditLogEntry) -> None:
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO audit_log (id, entity_type, entity_id, action, actor, detail,
                    occurred_at) VALUES (?,?,?,?,?,?,?)""",
                (entry.id, entry.entity_type, entry.entity_id, entry.action, entry.actor,
                 entry.detail, _dt(entry.occurred_at)),
            )

    def list_audit(self, entity_id: str | None = None) -> list[sqlite3.Row]:
        with self._conn() as conn:
            if entity_id:
                return conn.execute(
                    "SELECT * FROM audit_log WHERE entity_id = ? ORDER BY occurred_at", (entity_id,)
                ).fetchall()
            return conn.execute("SELECT * FROM audit_log ORDER BY occurred_at").fetchall()
