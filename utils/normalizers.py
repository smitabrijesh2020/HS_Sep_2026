"""Stdlib-only normalization helpers for values coming out of real workbooks.

Real exported spreadsheets are messy in predictable ways: header names and
cell values carry stray whitespace (including non-breaking space, U+00A0),
employee IDs round-trip through Excel as floats (`100234.0`), emails vary in
case, and "blank" shows up as None, "", or a handful of literal placeholder
strings. Every function here is a pure, dependency-free normalization step -
none of them decide business meaning (pass/fail, match/no-match); that
belongs to the services that call these.
"""
from __future__ import annotations

from datetime import date, datetime

# Prefixes/markers commonly used in source exports to mean "no value".
BLANK_MARKERS: frozenset[str] = frozenset({"", "n/a", "na", "-", "none", "null", "nil"})

# Tried in order; the first one that parses the whole string wins.
_DATE_FORMATS: tuple[str, ...] = (
    "%Y-%m-%d",
    "%Y-%m-%d %H:%M:%S",
    "%d-%b-%Y %I:%M %p",
    "%d-%b-%Y",
    "%d/%m/%Y",
    "%m/%d/%Y",
)


def normalize_whitespace(value: object) -> str:
    """None/NaN -> ''. Collapses any whitespace run (including U+00A0) to a
    single space and strips both ends."""
    if value is None:
        return ""
    if isinstance(value, float) and value != value:  # NaN != NaN
        return ""
    text = str(value)
    return " ".join(text.split())


def normalize_header_name(value: str) -> str:
    """Display/compare form for a real column header, e.g. turns
    '"Total_Questions "' into 'Total_Questions'."""
    return normalize_whitespace(value)


def normalize_header_key(value: str) -> str:
    """Aggressive form used only for loose classification matching (e.g.
    'Emp ID' ~ 'EMPLID' ~ 'Employee_ID'). Never used to auto-confirm a
    mapping - suggestion only."""
    return "".join(ch for ch in normalize_header_name(value).lower() if ch.isalnum())


def normalize_employee_id(value: object) -> str:
    """Normalize an employee identifier read from any source cell type.

    Handles the specific 'decimal-stored employee ID' problem: Excel/pandas
    frequently represent a whole-number ID column as float (100234.0). That
    must compare equal to the same ID read as int (100234) or str ('100234').
    """
    if value is None:
        return ""
    if isinstance(value, float):
        if value != value:  # NaN
            return ""
        if value.is_integer():
            return str(int(value))
        return normalize_whitespace(value)
    if isinstance(value, int):
        return str(value)
    return normalize_whitespace(value)


def normalize_email(value: object) -> str:
    """None/NaN -> ''. Trims and case-folds for comparison."""
    return normalize_whitespace(value).lower()


def is_valid_email_shape(value: str) -> bool:
    """Cheap structural check - exactly one '@' with a '.' somewhere after
    it. Deliberately not a full RFC validator; this only distinguishes
    "plausible email" from "clearly not an email" for error reporting."""
    if value.count("@") != 1:
        return False
    local, _, domain = value.partition("@")
    return bool(local) and "." in domain and not domain.startswith(".") and not domain.endswith(".")


def normalize_name(value: object) -> str:
    """Display form: None/NaN -> '', whitespace normalized, case preserved."""
    return normalize_whitespace(value)


def normalize_name_for_matching(value: object) -> str:
    """Case-insensitive comparison form of a person's name."""
    return normalize_name(value).lower()


def is_blank(value: object) -> bool:
    """True for None/NaN, empty string, or a known placeholder-for-blank
    marker (case/whitespace insensitive)."""
    text = normalize_whitespace(value)
    return text.lower() in BLANK_MARKERS


def normalize_status_text(value: object) -> str:
    """Comparison form for a free-text/status cell: whitespace-normalized,
    lower-cased. Feeds services.status_mapping_service, not a decision
    itself."""
    return normalize_whitespace(value).lower()


def parse_flexible_date(value: object) -> datetime | None:
    """Best-effort date parse that never raises.

    Real workbooks mix genuine datetime cells (when Excel applied a date
    format) with plain date-like strings (when it didn't). Returns None on
    anything unparseable so callers can route to DataUnavailable instead of
    crashing on a malformed date cell.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    if isinstance(value, float) and value != value:  # NaN
        return None
    text = normalize_whitespace(value)
    if not text or is_blank(text):
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None
