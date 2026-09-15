"""Enumerations shared across the domain, service, and persistence layers.

Kept dependency-free (stdlib `enum` only) so this module can be imported by
both the SQLAlchemy models and by pure business-logic code without pulling
in any framework.
"""
from __future__ import annotations

from enum import Enum


class ProgramStatus(str, Enum):
    DRAFT = "Draft"
    ACTIVE = "Active"
    CLOSED = "Closed"
    ARCHIVED = "Archived"


class BatchStatus(str, Enum):
    PLANNED = "Planned"
    OPEN = "Open"
    IN_PROGRESS = "InProgress"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"


class NominationStatus(str, Enum):
    DRAFT = "Draft"
    SUBMITTED = "Submitted"
    PENDING_VALIDATION = "PendingValidation"
    ELIGIBLE = "Eligible"
    REJECTED = "Rejected"
    WAITLISTED = "Waitlisted"
    CONFIRMED = "Confirmed"
    WITHDRAWN = "Withdrawn"
    COMPLETED = "Completed"


# States considered "active" for duplicate-nomination prevention purposes.
ACTIVE_NOMINATION_STATUSES = frozenset(
    {
        NominationStatus.DRAFT,
        NominationStatus.SUBMITTED,
        NominationStatus.PENDING_VALIDATION,
        NominationStatus.ELIGIBLE,
        NominationStatus.WAITLISTED,
        NominationStatus.CONFIRMED,
    }
)


class CheckSource(str, Enum):
    HS_REPORT = "HS_Report"
    DOSELECT = "DoSelect"
    IMOCHA = "iMocha"
    EXPERIENCE = "Experience"
    GRADE = "Grade"
    ROLE = "Role"
    REQUIRED_LEARNING = "RequiredLearning"
    MANUAL_OVERRIDE = "ManualOverride"
    OTHER = "Other"


class RuleResultStatus(str, Enum):
    PASS = "Pass"
    FAIL = "Fail"
    PENDING = "Pending"          # check not yet available
    NOT_APPLICABLE = "NotApplicable"
    DATA_UNAVAILABLE = "DataUnavailable"  # source system had no record - do not treat as Fail


class EligibilityStatus(str, Enum):
    ELIGIBLE = "Eligible"
    NOT_ELIGIBLE = "NotEligible"
    PENDING_CRITERIA = "PendingCriteria"     # one or more rules still pending/data unavailable
    PENDING_MANUAL_REVIEW = "PendingManualReview"


class CommunicationType(str, Enum):
    LAUNCH = "Launch"
    REMINDER_1 = "Reminder1"
    REMINDER_2 = "Reminder2"
    ESCALATION = "Escalation"
    FINAL_REMINDER = "FinalReminder"
    WELCOME = "Welcome"
    REJECTION = "Rejection"
    WAITLIST = "Waitlist"
    CLOSURE_REVIEW = "ClosureReview"


class CommunicationStatus(str, Enum):
    PENDING = "Pending"
    SENT = "Sent"
    DRY_RUN = "DryRun"
    SUPPRESSED = "Suppressed"     # idempotency / opt-out suppression
    FAILED = "Failed"
    RETRYING = "Retrying"


class ExportTargetSystem(str, Enum):
    FLARE = "FLARE"
    SF = "SF"


class ExportStatus(str, Enum):
    DRAFT = "Draft"
    VALIDATED = "Validated"
    VALIDATION_FAILED = "ValidationFailed"
    SUBMITTED = "Submitted"
