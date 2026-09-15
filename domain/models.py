"""Framework-agnostic domain entities for the first vertical slice.

These dataclasses represent the business objects independent of how they are
persisted (SQLAlchemy models in `repositories/orm_models.py` map onto the same
shape). Keeping this layer dependency-free means the eligibility engine,
dedup logic, and communication idempotency logic can be unit tested without
a database or any third-party package.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from domain.enums import (
    BatchStatus,
    CommunicationStatus,
    CommunicationType,
    EligibilityStatus,
    NominationStatus,
    ProgramStatus,
    RuleResultStatus,
)


def new_id() -> str:
    """Generate an enterprise-safe opaque identifier (UUID4 string).

    UUIDs are used instead of sequential integers so that internal record
    counts/order are not exposed through identifiers shared in exports,
    emails, or URLs.
    """
    return str(uuid.uuid4())


@dataclass
class Program:
    id: str = field(default_factory=new_id)
    name: str = ""
    description: str = ""
    owner: str = ""
    business_unit: str = ""
    technology: str = ""
    prerequisites: str = ""
    nomination_open_date: Optional[datetime] = None
    nomination_close_date: Optional[datetime] = None
    delivery_start_date: Optional[datetime] = None
    delivery_end_date: Optional[datetime] = None
    status: ProgramStatus = ProgramStatus.DRAFT
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = "system"
    updated_at: datetime = field(default_factory=datetime.utcnow)
    updated_by: str = "system"
    is_archived: bool = False


@dataclass
class Batch:
    id: str = field(default_factory=new_id)
    program_id: str = ""
    trf_number: str = ""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    capacity: int = 0
    trainer: str = ""
    location: str = ""
    delivery_mode: str = "Virtual"
    status: BatchStatus = BatchStatus.PLANNED
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = "system"
    updated_at: datetime = field(default_factory=datetime.utcnow)
    updated_by: str = "system"
    is_archived: bool = False

    def utilization(self, filled_seats: int) -> float:
        if self.capacity <= 0:
            return 0.0
        return round(filled_seats / self.capacity, 4)


@dataclass
class Employee:
    """Minimal synthetic learner record. Real employee PII must never be
    seeded into non-production environments; see docs/security_privacy_checklist.md.
    """
    id: str = field(default_factory=new_id)
    employee_code: str = ""
    display_name: str = ""
    email: str = ""
    manager_email: str = ""
    grade: str = ""
    location: str = ""
    is_active: bool = True


@dataclass
class Nomination:
    id: str = field(default_factory=new_id)
    employee_id: str = ""
    program_id: str = ""
    batch_id: str = ""
    status: NominationStatus = NominationStatus.DRAFT
    source: str = "Manual"  # Manual | CSV | XLSX
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = "system"
    updated_at: datetime = field(default_factory=datetime.utcnow)
    updated_by: str = "system"
    is_archived: bool = False


@dataclass
class EligibilityRuleResult:
    id: str = field(default_factory=new_id)
    nomination_id: str = ""
    rule_source: str = ""          # domain.enums.CheckSource value
    rule_name: str = ""
    result: RuleResultStatus = RuleResultStatus.PENDING
    detail: str = ""               # human-readable reason for this single rule
    evaluated_at: datetime = field(default_factory=datetime.utcnow)
    is_manual_override: bool = False
    override_reason: Optional[str] = None
    override_actor: Optional[str] = None
    override_at: Optional[datetime] = None


@dataclass
class EligibilityDecision:
    id: str = field(default_factory=new_id)
    nomination_id: str = ""
    status: EligibilityStatus = EligibilityStatus.PENDING_CRITERIA
    reasons: tuple[str, ...] = field(default_factory=tuple)
    decided_at: datetime = field(default_factory=datetime.utcnow)
    decided_by: str = "EligibilityEngine"
    rule_result_ids: tuple[str, ...] = field(default_factory=tuple)


@dataclass
class CommunicationLogEntry:
    id: str = field(default_factory=new_id)
    nomination_id: str = ""
    employee_id: str = ""
    comm_type: CommunicationType = CommunicationType.LAUNCH
    template_version: str = "v1"
    idempotency_key: str = ""
    status: CommunicationStatus = CommunicationStatus.PENDING
    graph_message_id: Optional[str] = None
    retry_count: int = 0
    error_detail: Optional[str] = None   # must be sanitized before storage
    created_at: datetime = field(default_factory=datetime.utcnow)
    sent_at: Optional[datetime] = None


@dataclass
class AuditLogEntry:
    id: str = field(default_factory=new_id)
    entity_type: str = ""
    entity_id: str = ""
    action: str = ""
    actor: str = "system"
    detail: str = ""
    occurred_at: datetime = field(default_factory=datetime.utcnow)
