"""Employee identity matching and resolution against real source rows.

Two distinct operations, per masterprompt.md's EMPLOYEE MATCHING RULES:

  * `match_employee` - join a second file's row (e.g. an HS Report row) to
    an ALREADY-KNOWN employee. Priority: normalized ID, then normalized
    email, then exact name, then fuzzy name as a review suggestion only -
    fuzzy matching is never treated as automatic proof of identity.

  * `resolve_or_flag_new_employee` - the Nomination Tracker's own rows
    carry their own authoritative ID+name+email together; this decides
    whether to reuse an existing employee record or flag one for creation
    or manual review, without silently overwriting conflicting data.

Uses stdlib `difflib` only - no new fuzzy-matching dependency.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher
from enum import Enum
from typing import Iterable

from domain.models import Employee
from utils.normalizers import normalize_email, normalize_employee_id, normalize_name, normalize_name_for_matching


class MatchStatus(str, Enum):
    EXACT_MATCH = "ExactMatch"
    PROBABLE_MATCH_REVIEW_REQUIRED = "ProbableMatchReviewRequired"
    MULTIPLE_MATCHES = "MultipleMatches"
    NO_MATCH = "NoMatch"
    INVALID_SOURCE_RECORD = "InvalidSourceRecord"


@dataclass(frozen=True)
class MatchResult:
    status: MatchStatus
    employee_id: str | None
    matched_on: str  # "EmployeeID" | "Email" | "Name" | "Fuzzy" | ""
    candidates: tuple[str, ...] = field(default_factory=tuple)
    detail: str = ""


@dataclass
class EmployeeIndex:
    by_code: dict[str, str]      # normalized employee_code -> internal Employee.id
    by_email: dict[str, str]     # normalized email -> internal Employee.id
    by_name: dict[str, list[str]]  # normalized name -> [internal Employee.id, ...]


def build_employee_index(employees: Iterable[Employee]) -> EmployeeIndex:
    by_code: dict[str, str] = {}
    by_email: dict[str, str] = {}
    by_name: dict[str, list[str]] = {}
    for emp in employees:
        code_key = normalize_employee_id(emp.employee_code)
        if code_key:
            by_code[code_key] = emp.id
        email_key = normalize_email(emp.email)
        if email_key:
            by_email[email_key] = emp.id
        name_key = normalize_name_for_matching(emp.display_name)
        if name_key:
            by_name.setdefault(name_key, []).append(emp.id)
    return EmployeeIndex(by_code=by_code, by_email=by_email, by_name=by_name)


def match_employee(
    row_employee_id: object,
    row_email: object,
    row_name: object,
    index: EmployeeIndex,
    fuzzy_threshold: float = 0.90,
) -> MatchResult:
    """Join a source row to an existing employee. Never raises."""
    id_key = normalize_employee_id(row_employee_id)
    email_key = normalize_email(row_email)
    name_key = normalize_name_for_matching(row_name)

    if not id_key and not email_key and not name_key:
        return MatchResult(
            MatchStatus.INVALID_SOURCE_RECORD, None, "",
            detail="Row has no usable employee identifier (ID, email, and name are all blank).",
        )

    if id_key and id_key in index.by_code:
        return MatchResult(MatchStatus.EXACT_MATCH, index.by_code[id_key], "EmployeeID")

    if email_key and email_key in index.by_email:
        return MatchResult(MatchStatus.EXACT_MATCH, index.by_email[email_key], "Email")

    if name_key and name_key in index.by_name:
        candidates = index.by_name[name_key]
        if len(candidates) == 1:
            return MatchResult(MatchStatus.EXACT_MATCH, candidates[0], "Name")
        return MatchResult(
            MatchStatus.MULTIPLE_MATCHES, None, "Name", candidates=tuple(candidates),
            detail=f"{len(candidates)} existing employees share this exact name - needs manual review.",
        )

    if name_key:
        best_ids: list[str] = []
        best_score = 0.0
        for existing_name_key, ids in index.by_name.items():
            score = SequenceMatcher(None, name_key, existing_name_key).ratio()
            if score > best_score:
                best_score, best_ids = score, ids
        if best_score >= fuzzy_threshold:
            employee_id = best_ids[0] if len(best_ids) == 1 else None
            return MatchResult(
                MatchStatus.PROBABLE_MATCH_REVIEW_REQUIRED, employee_id, "Fuzzy",
                candidates=tuple(best_ids),
                detail=f"Name similarity {best_score:.2f} against an existing record - "
                f"requires manual confirmation, never treated as automatic proof of identity.",
            )

    return MatchResult(MatchStatus.NO_MATCH, None, "", detail="No matching employee found by ID, email, or name.")


class RegistrationAction(str, Enum):
    USE_EXISTING = "UseExisting"
    CREATE_NEW = "CreateNew"
    MANUAL_CODE_REQUIRED = "ManualCodeRequired"
    CONFLICT_REVIEW_REQUIRED = "ConflictReviewRequired"
    INVALID_RECORD = "InvalidRecord"


@dataclass(frozen=True)
class RegistrationResult:
    action: RegistrationAction
    employee_id: str | None
    normalized_code: str
    normalized_email: str
    normalized_name: str
    detail: str = ""


def resolve_or_flag_new_employee(
    row_employee_id: object, row_name: object, row_email: object, index: EmployeeIndex,
) -> RegistrationResult:
    """Resolve a Nomination Tracker row's own (ID, name, email) triple
    against known employees. Never fabricates a missing employee code."""
    code_key = normalize_employee_id(row_employee_id)
    email_key = normalize_email(row_email)
    name_key = normalize_name(row_name)

    if not code_key and not email_key:
        return RegistrationResult(
            RegistrationAction.INVALID_RECORD, None, code_key, email_key, name_key,
            detail="Row has neither an employee ID nor an email - cannot register or match.",
        )

    if code_key and code_key in index.by_code:
        existing_id = index.by_code[code_key]
        if email_key and email_key in index.by_email and index.by_email[email_key] != existing_id:
            return RegistrationResult(
                RegistrationAction.CONFLICT_REVIEW_REQUIRED, None, code_key, email_key, name_key,
                detail="This row's employee ID and email point to two different existing employee "
                "records - needs manual review before import.",
            )
        detail = ""
        if email_key and email_key not in index.by_email:
            detail = "Email on this row differs from any email on file for this employee - not overwritten automatically."
        return RegistrationResult(RegistrationAction.USE_EXISTING, existing_id, code_key, email_key, name_key, detail)

    if code_key:
        # First time this ID has been seen - full confidence, since ID/name/email
        # all came from the same authoritative row.
        return RegistrationResult(RegistrationAction.CREATE_NEW, None, code_key, email_key, name_key)

    if email_key in index.by_email:
        return RegistrationResult(
            RegistrationAction.USE_EXISTING, index.by_email[email_key], code_key, email_key, name_key
        )

    return RegistrationResult(
        RegistrationAction.MANUAL_CODE_REQUIRED, None, code_key, email_key, name_key,
        detail="No employee ID on this row and the email does not match an existing employee - "
        "a unique employee code must be assigned manually before this row can be imported.",
    )
