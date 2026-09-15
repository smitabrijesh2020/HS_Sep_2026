"""Dry-run communication service: idempotency, duplicate suppression, retry.

Per requirements, the scheduler/communication path must:
  1. Generate a deterministic idempotency key.
  2. Check communication history before sending.
  3. Send via the configured provider or simulate in dry-run mode.
  4. Record success / failure / suppression / retry status.
  5. Never expose secrets or raw employee PII in logs/error details.

This module is provider-agnostic: it takes a `send_fn` callable so tests can
inject a fake and production code can inject the Microsoft Graph client.
No network or database dependency lives here.
"""
from __future__ import annotations

import hashlib
from dataclasses import replace
from datetime import datetime
from typing import Callable, Iterable

from domain.enums import CommunicationStatus, CommunicationType
from domain.models import CommunicationLogEntry
from security.redaction import sanitize_error


class SendResult:
    def __init__(self, success: bool, provider_message_id: str | None = None, error: str | None = None):
        self.success = success
        self.provider_message_id = provider_message_id
        self.error = error


def build_idempotency_key(
    employee_id: str,
    nomination_id: str,
    comm_type: CommunicationType,
    template_version: str,
    schedule_date: str,
) -> str:
    """Deterministic key so retried/overlapping scheduler runs can never
    produce two sends for the same (employee, nomination, comm_type,
    template_version, schedule_date) tuple."""
    raw = "|".join([employee_id, nomination_id, comm_type.value, template_version, schedule_date])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def has_already_succeeded(
    idempotency_key: str, existing_log: Iterable[CommunicationLogEntry]
) -> bool:
    return any(
        entry.idempotency_key == idempotency_key and entry.status == CommunicationStatus.SENT
        for entry in existing_log
    )


def _sanitize_error(error: str | None) -> str | None:
    return sanitize_error(error)


def dispatch(
    employee_id: str,
    nomination_id: str,
    comm_type: CommunicationType,
    template_version: str,
    schedule_date: str,
    existing_log: Iterable[CommunicationLogEntry],
    send_fn: Callable[[], SendResult],
    dry_run: bool = True,
    max_retries: int = 3,
    attempt: int = 0,
) -> CommunicationLogEntry:
    """Evaluate idempotency, then send (or simulate) and return a log entry.

    Callers are responsible for persisting the returned entry and for
    invoking `dispatch` again (with an incremented `attempt`) on transient
    failure, e.g. from the scheduler's backoff loop.
    """
    key = build_idempotency_key(employee_id, nomination_id, comm_type, template_version, schedule_date)

    if has_already_succeeded(key, existing_log):
        return CommunicationLogEntry(
            nomination_id=nomination_id,
            employee_id=employee_id,
            comm_type=comm_type,
            template_version=template_version,
            idempotency_key=key,
            status=CommunicationStatus.SUPPRESSED,
            retry_count=attempt,
        )

    if dry_run:
        return CommunicationLogEntry(
            nomination_id=nomination_id,
            employee_id=employee_id,
            comm_type=comm_type,
            template_version=template_version,
            idempotency_key=key,
            status=CommunicationStatus.DRY_RUN,
            retry_count=attempt,
            sent_at=datetime.utcnow(),
        )

    result = send_fn()
    if result.success:
        return CommunicationLogEntry(
            nomination_id=nomination_id,
            employee_id=employee_id,
            comm_type=comm_type,
            template_version=template_version,
            idempotency_key=key,
            status=CommunicationStatus.SENT,
            graph_message_id=result.provider_message_id,
            retry_count=attempt,
            sent_at=datetime.utcnow(),
        )

    status = CommunicationStatus.RETRYING if attempt < max_retries else CommunicationStatus.FAILED
    return CommunicationLogEntry(
        nomination_id=nomination_id,
        employee_id=employee_id,
        comm_type=comm_type,
        template_version=template_version,
        idempotency_key=key,
        status=status,
        retry_count=attempt,
        error_detail=_sanitize_error(result.error),
    )


def backoff_seconds(attempt: int, base: float = 2.0, cap: float = 300.0) -> float:
    """Exponential backoff with a cap, for transient send failures."""
    return min(cap, base ** max(1, attempt))
