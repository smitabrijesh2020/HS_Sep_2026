"""Domain shapes for source-file discovery and column mapping.

Pure dataclasses/enums, no I/O - same convention as `domain/models.py`. The
services that read real workbooks (`services/workbook_inspector.py`) and
that persist mapping decisions (`services/mapping_config_service.py`) both
build and consume these shapes; nothing here touches a file or a database.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class SourceKind(str, Enum):
    NOMINATION_TRACKER = "NominationTracker"
    HS_REPORT = "HSReport"
    DOSELECT_REPORT = "DoSelectReport"
    IMOCHA_REPORT = "IMochaReport"
    PROGRAM_BATCH_MASTER = "ProgramBatchMaster"
    MAIL_TEMPLATE = "MailTemplate"
    OTHER = "Other"
    UNKNOWN = "Unknown"


class CanonicalField(str, Enum):
    EMPLOYEE_ID = "EmployeeID"
    EMPLOYEE_NAME = "EmployeeName"
    EMPLOYEE_EMAIL = "EmployeeEmail"
    MANAGER_EMAIL = "ManagerEmail"
    HS_SPOC_EMAIL = "HSSPOCEmail"
    PROGRAM_ID = "ProgramID"
    PROGRAM_NAME = "ProgramName"
    NOMINATION_DATE = "NominationDate"
    NOMINATION_STATUS = "NominationStatus"
    HS_COMPLETION_STATUS = "HSCompletionStatus"
    HS_COMPLETION_DATE = "HSCompletionDate"
    DOSELECT_STATUS = "DoSelectStatus"
    DOSELECT_COMPLETION_DATE = "DoSelectCompletionDate"
    IMOCHA_STATUS = "IMochaStatus"
    IMOCHA_COMPLETION_DATE = "IMochaCompletionDate"
    OVERALL_ELIGIBILITY = "OverallEligibility"
    MISSING_PREREQUISITES = "MissingPrerequisites"
    ELIGIBILITY_REASON = "EligibilityReason"
    DELTA_STATUS = "DeltaStatus"
    DELTA_REASON = "DeltaReason"
    REMINDER_STAGE = "ReminderStage"
    REMINDER_COUNT = "ReminderCount"
    LAST_REMINDER_DATE = "LastReminderDate"
    WELCOME_MAIL_STATUS = "WelcomeMailStatus"
    FLARE_STATUS = "FLAREStatus"
    SUCCESS_FACTORS_STATUS = "SuccessFactorsStatus"
    CLOSURE_STATUS = "ClosureStatus"


# Canonical fields this increment's Column Mapping screen and adapter
# actually read. The remaining CanonicalField values exist for schema
# completeness with masterprompt.md's full vocabulary but are not consumed
# until later increments (Delta, Communications, FLARE/SF, Reminders).
ACTIVE_CANONICAL_FIELDS_BY_SOURCE: dict[SourceKind, tuple[CanonicalField, ...]] = {
    SourceKind.NOMINATION_TRACKER: (
        CanonicalField.EMPLOYEE_ID,
        CanonicalField.EMPLOYEE_NAME,
        CanonicalField.EMPLOYEE_EMAIL,
        CanonicalField.PROGRAM_NAME,
        CanonicalField.NOMINATION_DATE,
        CanonicalField.NOMINATION_STATUS,
        CanonicalField.DOSELECT_STATUS,
    ),
    SourceKind.HS_REPORT: (
        CanonicalField.EMPLOYEE_ID,
        CanonicalField.EMPLOYEE_EMAIL,
        CanonicalField.PROGRAM_NAME,
        CanonicalField.HS_COMPLETION_STATUS,
        CanonicalField.HS_COMPLETION_DATE,
    ),
    SourceKind.DOSELECT_REPORT: (
        CanonicalField.EMPLOYEE_ID,
        CanonicalField.EMPLOYEE_EMAIL,
        CanonicalField.DOSELECT_STATUS,
        CanonicalField.DOSELECT_COMPLETION_DATE,
    ),
    SourceKind.IMOCHA_REPORT: (
        CanonicalField.EMPLOYEE_ID,
        CanonicalField.EMPLOYEE_EMAIL,
        CanonicalField.IMOCHA_STATUS,
        CanonicalField.IMOCHA_COMPLETION_DATE,
    ),
}


class MappingFieldStatus(str, Enum):
    MAPPED = "Mapped"
    UNRESOLVED = "Unresolved"
    UNSTRUCTURED_NEEDS_REVIEW = "UnstructuredNeedsReview"


@dataclass(frozen=True)
class FieldMapping:
    canonical_field: CanonicalField
    status: MappingFieldStatus
    source_column: str | None = None  # normalized header name, or None if unresolved
    note: str = ""


@dataclass
class SourceMapping:
    source_kind: SourceKind
    file_path: str
    sheet_name: str
    header_row_index: int
    raw_headers: tuple[str, ...]
    header_signature: str
    field_mappings: dict[CanonicalField, FieldMapping] = field(default_factory=dict)
    program_filter_aliases: dict[str, tuple[str, ...]] = field(default_factory=dict)
    confirmed_by: str = ""
    confirmed_at: datetime | None = None
    last_validated_at: datetime | None = None


@dataclass
class MappingConfig:
    version: int = 1
    sources: dict[str, SourceMapping] = field(default_factory=dict)  # keyed by SourceKind.value


@dataclass(frozen=True)
class DiscoveredFile:
    file_path: str
    extension: str
    is_supported: bool
    skip_reason: str | None = None


@dataclass(frozen=True)
class SheetInspection:
    sheet_name: str
    raw_headers: tuple[str, ...]
    normalized_headers: tuple[str, ...]
    header_row_index: int
    data_row_count: int
    sample_issue: str | None = None


@dataclass(frozen=True)
class WorkbookInspection:
    file_path: str
    file_size_bytes: int
    modified_at: datetime | None
    sheets: tuple[SheetInspection, ...]
    open_error: str | None = None


@dataclass(frozen=True)
class ClassificationSuggestion:
    source_kind: SourceKind
    confidence: float
    matched_keywords: tuple[str, ...]
    reason: str
