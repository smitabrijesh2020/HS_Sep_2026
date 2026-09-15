"""Nomination lifecycle logic: creation with duplicate-active-nomination prevention.

Business rule (per requirements): an employee must not have more than one
*active* nomination for the same program + batch at a time. "Active" is
defined in `domain.enums.ACTIVE_NOMINATION_STATUSES`.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from typing import Iterable

from domain.enums import ACTIVE_NOMINATION_STATUSES, NominationStatus
from domain.models import AuditLogEntry, Nomination


class DuplicateActiveNominationError(Exception):
    """Raised when an employee already has an active nomination for the same
    program + batch."""


def find_duplicate_active_nomination(
    existing_nominations: Iterable[Nomination],
    employee_id: str,
    program_id: str,
    batch_id: str,
) -> Nomination | None:
    for nom in existing_nominations:
        if (
            nom.employee_id == employee_id
            and nom.program_id == program_id
            and nom.batch_id == batch_id
            and nom.status in ACTIVE_NOMINATION_STATUSES
            and not nom.is_archived
        ):
            return nom
    return None


def create_nomination(
    existing_nominations: Iterable[Nomination],
    employee_id: str,
    program_id: str,
    batch_id: str,
    actor: str,
    source: str = "Manual",
) -> tuple[Nomination, AuditLogEntry]:
    """Create a new nomination after checking for an active duplicate.

    Raises DuplicateActiveNominationError instead of silently creating a
    second row, so callers (UI / bulk-upload service) can surface a clear
    validation message rather than producing duplicate communications later.
    """
    dup = find_duplicate_active_nomination(existing_nominations, employee_id, program_id, batch_id)
    if dup is not None:
        raise DuplicateActiveNominationError(
            f"Employee {employee_id} already has an active nomination "
            f"(id={dup.id}, status={dup.status.value}) for program={program_id}, batch={batch_id}."
        )

    nomination = Nomination(
        employee_id=employee_id,
        program_id=program_id,
        batch_id=batch_id,
        status=NominationStatus.SUBMITTED,
        source=source,
        created_by=actor,
        updated_by=actor,
    )
    audit = AuditLogEntry(
        entity_type="Nomination",
        entity_id=nomination.id,
        action="Created",
        actor=actor,
        detail=f"Nomination created via {source} for employee={employee_id}, "
        f"program={program_id}, batch={batch_id}.",
    )
    return nomination, audit


def transition_status(
    nomination: Nomination, new_status: NominationStatus, actor: str, reason: str = ""
) -> tuple[Nomination, AuditLogEntry]:
    """Return an updated copy of the nomination with a new status, plus an
    audit entry. Pure function - caller is responsible for persistence."""
    updated = replace(nomination, status=new_status, updated_at=datetime.utcnow(), updated_by=actor)
    audit = AuditLogEntry(
        entity_type="Nomination",
        entity_id=nomination.id,
        action="StatusChanged",
        actor=actor,
        detail=f"{nomination.status.value} -> {new_status.value}. Reason: {reason or 'n/a'}",
    )
    return updated, audit
