"""FLARE and SF export framework - column-mapping template ONLY.

IMPORTANT / ASSUMPTION FLAGGED FOR REVIEW: no FLARE or SuccessFactors (SF)
target-system field specification was supplied in the project folder. Per
the working rules, this module does NOT invent a target schema. Instead it
provides:
  1. A clearly labeled, editable mapping template (`DEFAULT_FLARE_MAPPING`,
     `DEFAULT_SF_MAPPING`) using the source fields already visible in the
     current BAU trackers (Emp ID, Name, Email, Certification/Program,
     TRF/Batch, Prerequisite/Eligibility Status) as placeholders.
  2. Row-level validation (required fields, duplicate detection) that the
     real column list can be swapped into once FLARE/SF specs are provided.

Stop and request the actual target schema from the FLARE/SF system owner
before this export is used for a real submission.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

# Mapping: target_column_name -> function(nomination_row: dict) -> value
# `nomination_row` is expected to carry the joined fields from nominations +
# employees + programs + batches + latest eligibility decision.
DEFAULT_FLARE_MAPPING: dict[str, Callable[[dict], object]] = {
    "EmployeeID": lambda r: r.get("employee_code"),
    "EmployeeName": lambda r: r.get("display_name"),
    "EmailAddress": lambda r: r.get("email"),
    "ProgramName": lambda r: r.get("program_name"),
    "TRFNumber": lambda r: r.get("trf_number"),
    "EligibilityStatus": lambda r: r.get("eligibility_status"),
    "NominationStatus": lambda r: r.get("nomination_status"),
}

DEFAULT_SF_MAPPING: dict[str, Callable[[dict], object]] = {
    "PersonIdExternal": lambda r: r.get("employee_code"),
    "CourseId": lambda r: r.get("program_name"),
    "SessionId": lambda r: r.get("trf_number"),
    "Status": lambda r: r.get("nomination_status"),
}

REQUIRED_FIELDS = ("employee_code", "display_name", "email", "program_name", "trf_number")


@dataclass
class ExportValidationError:
    row_index: int
    field: str
    message: str


@dataclass
class ExportResult:
    target_system: str
    rows: list[dict] = field(default_factory=list)
    errors: list[ExportValidationError] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.errors


def validate_rows(rows: list[dict]) -> list[ExportValidationError]:
    errors: list[ExportValidationError] = []
    seen_keys: set[tuple] = set()
    for idx, row in enumerate(rows):
        for f in REQUIRED_FIELDS:
            if not row.get(f):
                errors.append(ExportValidationError(idx, f, f"Required field '{f}' is missing."))
        key = (row.get("employee_code"), row.get("trf_number"))
        if key in seen_keys:
            errors.append(ExportValidationError(idx, "employee_code+trf_number", "Duplicate export row."))
        seen_keys.add(key)
    return errors


def build_export(
    source_rows: list[dict],
    target_system: str,
    mapping: dict[str, Callable[[dict], object]],
) -> ExportResult:
    errors = validate_rows(source_rows)
    mapped_rows = [{col: fn(r) for col, fn in mapping.items()} for r in source_rows]
    return ExportResult(target_system=target_system, rows=mapped_rows, errors=errors)
