"""Persistence and drift-validation for column-mapping configuration.

Mapping config files contain real column header names (schema) but never
real data values, and are still kept out of git (`.gitignore`) alongside
`.env`/`*.db` since header names alone can reveal internal structure. Only
the `.example.json` templates are tracked.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Sequence

from domain.mapping_models import (
    CanonicalField,
    FieldMapping,
    MappingConfig,
    MappingFieldStatus,
    SheetInspection,
    SourceMapping,
)
from domain.mapping_models import SourceKind


def new_empty_config() -> MappingConfig:
    return MappingConfig()


def compute_header_signature(normalized_headers: Sequence[str]) -> str:
    """Order-independent fingerprint of a sheet's header set, used to detect
    drift without caring whether columns were merely reordered."""
    joined = "|".join(sorted(h for h in normalized_headers if h))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def _mapping_to_dict(mapping: SourceMapping) -> dict:
    return {
        "source_kind": mapping.source_kind.value,
        "file_path": mapping.file_path,
        "sheet_name": mapping.sheet_name,
        "header_row_index": mapping.header_row_index,
        "raw_headers": list(mapping.raw_headers),
        "header_signature": mapping.header_signature,
        "field_mappings": {
            cf.value: {
                "status": fm.status.value,
                "source_column": fm.source_column,
                "note": fm.note,
            }
            for cf, fm in mapping.field_mappings.items()
        },
        "program_filter_aliases": {k: list(v) for k, v in mapping.program_filter_aliases.items()},
        "confirmed_by": mapping.confirmed_by,
        "confirmed_at": mapping.confirmed_at.isoformat() if mapping.confirmed_at else None,
        "last_validated_at": mapping.last_validated_at.isoformat() if mapping.last_validated_at else None,
    }


def _mapping_from_dict(data: dict) -> SourceMapping:
    return SourceMapping(
        source_kind=SourceKind(data["source_kind"]),
        file_path=data["file_path"],
        sheet_name=data["sheet_name"],
        header_row_index=data["header_row_index"],
        raw_headers=tuple(data.get("raw_headers", [])),
        header_signature=data["header_signature"],
        field_mappings={
            CanonicalField(k): FieldMapping(
                canonical_field=CanonicalField(k),
                status=MappingFieldStatus(v["status"]),
                source_column=v.get("source_column"),
                note=v.get("note", ""),
            )
            for k, v in data.get("field_mappings", {}).items()
        },
        program_filter_aliases={k: tuple(v) for k, v in data.get("program_filter_aliases", {}).items()},
        confirmed_by=data.get("confirmed_by", ""),
        confirmed_at=datetime.fromisoformat(data["confirmed_at"]) if data.get("confirmed_at") else None,
        last_validated_at=(
            datetime.fromisoformat(data["last_validated_at"]) if data.get("last_validated_at") else None
        ),
    )


def load_mapping_config(path: Path) -> MappingConfig:
    """Missing file -> a fresh empty config, not an error (first run)."""
    if not path.exists():
        return new_empty_config()
    raw = json.loads(path.read_text(encoding="utf-8"))
    return MappingConfig(
        version=raw.get("version", 1),
        sources={k: _mapping_from_dict(v) for k, v in raw.get("sources", {}).items()},
    )


def save_mapping_config(config: MappingConfig, path: Path) -> None:
    payload = {
        "version": config.version,
        "sources": {k: _mapping_to_dict(v) for k, v in config.sources.items()},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def upsert_source_mapping(config: MappingConfig, mapping: SourceMapping) -> MappingConfig:
    """Pure - returns a new MappingConfig rather than mutating the input."""
    new_sources = dict(config.sources)
    new_sources[mapping.source_kind.value] = mapping
    return MappingConfig(version=config.version, sources=new_sources)


def unresolved_canonical_fields(
    mapping: SourceMapping, relevant: Sequence[CanonicalField]
) -> list[CanonicalField]:
    """Fields from `relevant` that are not cleanly Mapped (i.e. Unresolved or
    UnstructuredNeedsReview, or simply never configured at all)."""
    result = []
    for cf in relevant:
        fm = mapping.field_mappings.get(cf)
        if fm is None or fm.status != MappingFieldStatus.MAPPED:
            result.append(cf)
    return result


@dataclass(frozen=True)
class MappingValidationIssue:
    severity: str  # "error" | "warning"
    field: CanonicalField | None
    message: str


def validate_mapping_against_inspection(
    mapping: SourceMapping, current: SheetInspection
) -> list[MappingValidationIssue]:
    """Compare a saved mapping against a fresh inspection of the same sheet.

    A mapped column that has vanished is an error (the mapping can no longer
    do what it claims). Any other header drift (added/removed, unmapped
    columns) is a warning so the user notices without being blocked.
    """
    issues: list[MappingValidationIssue] = []
    current_headers = set(current.normalized_headers)

    vanished_mapped_columns: set[str] = set()
    for cf, fm in mapping.field_mappings.items():
        if fm.status == MappingFieldStatus.MAPPED and fm.source_column not in current_headers:
            vanished_mapped_columns.add(fm.source_column or "")
            issues.append(
                MappingValidationIssue(
                    severity="error",
                    field=cf,
                    message=f"Mapped column '{fm.source_column}' for {cf.value} is no longer present "
                    f"in the source file.",
                )
            )

    original_headers = set(mapping.raw_headers)
    added = sorted(current_headers - original_headers)
    removed = sorted((original_headers - current_headers) - vanished_mapped_columns)
    if added:
        issues.append(
            MappingValidationIssue(
                severity="warning", field=None,
                message=f"New columns appeared since this mapping was saved: {', '.join(added)}",
            )
        )
    if removed:
        issues.append(
            MappingValidationIssue(
                severity="warning", field=None,
                message=f"Columns removed since this mapping was saved: {', '.join(removed)}",
            )
        )
    return issues
