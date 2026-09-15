"""Read-only discovery and structural inspection of local source workbooks.

This is the only module allowed to open real business files. It reads
folder listings, sheet names, header rows, and row counts - never full data
rows during inspection/classification, and it must not crash the caller on
a single bad file (corrupted, locked, or password-protected workbooks are
reported as a sanitized `open_error`, per the acceptance rule that one bad
file must not take down the app).

`read_sheet_rows` is the one function here that reads full data - it is
only ever called by ingestion/matching services, never by the mapping
screen's discovery/preview flow, and its results must never be logged or
displayed verbatim (see docs/security_privacy_checklist.md).
"""
from __future__ import annotations

import zipfile
from pathlib import Path

import openpyxl
import pandas as pd
from openpyxl.utils.exceptions import InvalidFileException

from domain.mapping_models import (
    ClassificationSuggestion,
    DiscoveredFile,
    SheetInspection,
    SourceKind,
    WorkbookInspection,
)
from security.redaction import sanitize_error
from utils.normalizers import normalize_header_key, normalize_header_name

SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({".xlsx", ".xlsm"})

# Extensions the folder scan recognizes and labels, without attempting to
# open/parse them in this increment (masterprompt.md still wants them listed).
_KNOWN_UNSUPPORTED_LABELS: dict[str, str] = {
    ".msg": "Outlook message - classified by filename only, not parsed",
    ".docx": "Word document - not processed in this increment",
    ".pptx": "PowerPoint template - not processed in this increment",
    ".csv": "CSV - not yet supported by this increment's inspector",
}

# Keyword sets used for classification, drawn from the real headers found
# this session. Keys are already run through normalize_header_key.
_CLASSIFICATION_KEYWORDS: dict[SourceKind, tuple[str, ...]] = {
    SourceKind.NOMINATION_TRACKER: (
        "empid", "name", "email", "certificationname", "trfno", "prerequisitestatus",
    ),
    SourceKind.HS_REPORT: (
        "emplid", "empname", "emailid", "certificatename", "certificationstatus",
        "dateofcertification", "ishyperscaler",
    ),
    SourceKind.IMOCHA_REPORT: (
        "employeeid", "candidatename", "candidateemailaddress", "testid", "testname",
        "teststatus", "testscore", "percentage", "proctoringflag",
    ),
    SourceKind.DOSELECT_REPORT: (
        "doselect", "doselectstatus", "doselectscore", "employeeid", "email",
    ),
    SourceKind.PROGRAM_BATCH_MASTER: (
        "certificationname", "trf", "trainername", "touchpoint", "month",
    ),
}
_CLASSIFICATION_CONFIDENCE_FLOOR = 0.34


def list_source_files(folder: Path, recursive: bool = False) -> list[DiscoveredFile]:
    """List files directly in `folder` (or recursively), classified only by
    extension. Never raises on an individual entry - a file whose stat()
    fails is skipped from the listing rather than aborting the scan."""
    if not folder.exists():
        raise FileNotFoundError(f"Source folder does not exist: {folder}")
    if not folder.is_dir():
        raise NotADirectoryError(f"Source folder path is not a directory: {folder}")

    iterator = folder.rglob("*") if recursive else folder.iterdir()
    discovered: list[DiscoveredFile] = []
    for entry in iterator:
        if not entry.is_file():
            continue
        ext = entry.suffix.lower()
        if ext in SUPPORTED_EXTENSIONS:
            discovered.append(DiscoveredFile(file_path=str(entry), extension=ext, is_supported=True))
        else:
            reason = _KNOWN_UNSUPPORTED_LABELS.get(ext, f"Unsupported file type '{ext}'")
            discovered.append(
                DiscoveredFile(file_path=str(entry), extension=ext, is_supported=False, skip_reason=reason)
            )
    return discovered


def inspect_workbook(file_path: Path, header_row_index: int = 1) -> WorkbookInspection:
    """Open a workbook read-only and report sheet names, header rows, and
    row counts. Never raises - any failure to open is captured as a
    sanitized `open_error` on the returned WorkbookInspection instead."""
    try:
        stat = file_path.stat()
        size_bytes = stat.st_size
        modified_at = _safe_mtime(stat.st_mtime)
    except OSError as exc:
        return WorkbookInspection(
            file_path=str(file_path), file_size_bytes=0, modified_at=None, sheets=(),
            open_error=sanitize_error(f"Could not read file metadata: {exc}"),
        )

    try:
        workbook = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
    except PermissionError:
        return WorkbookInspection(
            file_path=str(file_path), file_size_bytes=size_bytes, modified_at=modified_at, sheets=(),
            open_error="File appears to be open in another program (locked for reading).",
        )
    except (InvalidFileException, zipfile.BadZipFile, KeyError, OSError) as exc:
        return WorkbookInspection(
            file_path=str(file_path), file_size_bytes=size_bytes, modified_at=modified_at, sheets=(),
            open_error=sanitize_error(
                f"Could not open workbook - it may be corrupted, password-protected, "
                f"or not a valid .xlsx/.xlsm file ({exc.__class__.__name__})."
            ),
        )

    sheets: list[SheetInspection] = []
    try:
        for sheet_name in workbook.sheetnames:
            ws = workbook[sheet_name]
            header_row = _nth_row(ws, header_row_index)
            raw_headers = tuple("" if v is None else str(v) for v in header_row)
            normalized_headers = tuple(normalize_header_name(v) for v in raw_headers)
            data_row_count = max((ws.max_row or header_row_index) - header_row_index, 0)
            sample_issue = None
            if not any(normalized_headers):
                sample_issue = "Header row is blank - confirm header_row_index for this sheet."
            sheets.append(
                SheetInspection(
                    sheet_name=sheet_name,
                    raw_headers=raw_headers,
                    normalized_headers=normalized_headers,
                    header_row_index=header_row_index,
                    data_row_count=data_row_count,
                    sample_issue=sample_issue,
                )
            )
    except Exception as exc:  # defensive: one malformed sheet must not lose the whole inspection
        return WorkbookInspection(
            file_path=str(file_path), file_size_bytes=size_bytes, modified_at=modified_at,
            sheets=tuple(sheets),
            open_error=sanitize_error(f"Error while reading sheet structure: {exc}"),
        )
    finally:
        workbook.close()

    return WorkbookInspection(
        file_path=str(file_path), file_size_bytes=size_bytes, modified_at=modified_at,
        sheets=tuple(sheets),
    )


def _nth_row(ws, row_index: int) -> tuple:
    for i, row in enumerate(ws.iter_rows(min_row=row_index, max_row=row_index, values_only=True), start=1):
        return row
    return ()


def _safe_mtime(epoch_seconds: float):
    from datetime import datetime

    try:
        return datetime.fromtimestamp(epoch_seconds)
    except (OverflowError, OSError, ValueError):
        return None


def suggest_classification(sheet: SheetInspection) -> ClassificationSuggestion:
    """Keyword-overlap scoring against known header shapes. Never returns a
    confident suggestion above the floor unless enough keywords genuinely
    matched - this only pre-fills a suggestion; the mapping screen always
    requires explicit user confirmation, never auto-selection."""
    header_keys = {normalize_header_key(h) for h in sheet.normalized_headers if h}
    sheet_name_key = normalize_header_key(sheet.sheet_name)
    haystack = "|".join(sorted(header_keys)) + "|" + sheet_name_key

    best_kind = SourceKind.UNKNOWN
    best_score = 0.0
    best_matched: tuple[str, ...] = ()
    for kind, keywords in _CLASSIFICATION_KEYWORDS.items():
        matched = tuple(kw for kw in keywords if kw in haystack)
        score = len(matched) / len(keywords) if keywords else 0.0
        if score > best_score:
            best_kind, best_score, best_matched = kind, score, matched

    if best_score < _CLASSIFICATION_CONFIDENCE_FLOOR:
        return ClassificationSuggestion(
            source_kind=SourceKind.UNKNOWN, confidence=best_score, matched_keywords=(),
            reason="No source kind matched enough of its expected column headers.",
        )
    return ClassificationSuggestion(
        source_kind=best_kind, confidence=round(best_score, 2), matched_keywords=best_matched,
        reason=f"Matched {len(best_matched)} of {len(_CLASSIFICATION_KEYWORDS[best_kind])} "
        f"expected headers/keywords for {best_kind.value}.",
    )


def read_sheet_rows(file_path: Path, sheet_name: str, header_row_index: int = 1) -> list[dict[str, object]]:
    """Full data read for ingestion/matching only - never for display in the
    mapping screen. Keys are normalized header names. Drops fully-blank
    trailing rows; pads short rows with None so every dict has every key."""
    frame = pd.read_excel(
        file_path, sheet_name=sheet_name, header=header_row_index - 1, dtype=object,
    )
    frame = frame.dropna(how="all")
    normalized_columns = [normalize_header_name(str(c)) for c in frame.columns]
    frame.columns = normalized_columns
    return frame.to_dict(orient="records")
