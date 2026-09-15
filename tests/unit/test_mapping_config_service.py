"""Unit tests for services.mapping_config_service."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from domain.mapping_models import (
    CanonicalField,
    FieldMapping,
    MappingFieldStatus,
    SheetInspection,
    SourceKind,
    SourceMapping,
)
from services.mapping_config_service import (
    compute_header_signature,
    load_mapping_config,
    new_empty_config,
    save_mapping_config,
    unresolved_canonical_fields,
    upsert_source_mapping,
    validate_mapping_against_inspection,
)


def _sample_mapping() -> SourceMapping:
    headers = ("Emp ID", "Name", "Email", "Certification Name", "TRF No.", "Prerequisite Status")
    return SourceMapping(
        source_kind=SourceKind.NOMINATION_TRACKER,
        file_path="Nominations - Aug 2026_5.0_To_Share.xlsx",
        sheet_name="Nominations",
        header_row_index=1,
        raw_headers=headers,
        header_signature=compute_header_signature(headers),
        field_mappings={
            CanonicalField.EMPLOYEE_ID: FieldMapping(
                CanonicalField.EMPLOYEE_ID, MappingFieldStatus.MAPPED, "Emp ID"
            ),
            CanonicalField.EMPLOYEE_EMAIL: FieldMapping(
                CanonicalField.EMPLOYEE_EMAIL, MappingFieldStatus.MAPPED, "Email"
            ),
            CanonicalField.DOSELECT_STATUS: FieldMapping(
                CanonicalField.DOSELECT_STATUS, MappingFieldStatus.UNSTRUCTURED_NEEDS_REVIEW,
                "Prerequisite Status", note="Free text - not auto-interpreted.",
            ),
        },
    )


class TestRoundTrip(unittest.TestCase):
    def test_save_then_load_reproduces_config(self):
        config = upsert_source_mapping(new_empty_config(), _sample_mapping())
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "column_mappings.json"
            save_mapping_config(config, path)
            reloaded = load_mapping_config(path)

        mapping = reloaded.sources[SourceKind.NOMINATION_TRACKER.value]
        self.assertEqual(mapping.sheet_name, "Nominations")
        self.assertEqual(
            mapping.field_mappings[CanonicalField.EMPLOYEE_ID].source_column, "Emp ID"
        )
        self.assertEqual(
            mapping.field_mappings[CanonicalField.DOSELECT_STATUS].status,
            MappingFieldStatus.UNSTRUCTURED_NEEDS_REVIEW,
        )

    def test_missing_file_returns_empty_config_not_error(self):
        config = load_mapping_config(Path("Z:/does/not/exist/column_mappings.json"))
        self.assertEqual(config.sources, {})


class TestUnresolvedCanonicalFields(unittest.TestCase):
    def test_mapped_field_is_not_unresolved(self):
        mapping = _sample_mapping()
        unresolved = unresolved_canonical_fields(mapping, [CanonicalField.EMPLOYEE_ID])
        self.assertEqual(unresolved, [])

    def test_unstructured_field_is_unresolved(self):
        mapping = _sample_mapping()
        unresolved = unresolved_canonical_fields(mapping, [CanonicalField.DOSELECT_STATUS])
        self.assertEqual(unresolved, [CanonicalField.DOSELECT_STATUS])

    def test_never_configured_field_is_unresolved(self):
        mapping = _sample_mapping()
        unresolved = unresolved_canonical_fields(mapping, [CanonicalField.MANAGER_EMAIL])
        self.assertEqual(unresolved, [CanonicalField.MANAGER_EMAIL])


class TestValidateMappingAgainstInspection(unittest.TestCase):
    def test_unchanged_headers_produce_no_issues(self):
        mapping = _sample_mapping()
        current = SheetInspection(
            sheet_name="Nominations", raw_headers=mapping.raw_headers,
            normalized_headers=mapping.raw_headers, header_row_index=1, data_row_count=10,
        )
        self.assertEqual(validate_mapping_against_inspection(mapping, current), [])

    def test_vanished_mapped_column_is_an_error(self):
        mapping = _sample_mapping()
        remaining = tuple(h for h in mapping.raw_headers if h != "Email")
        current = SheetInspection(
            sheet_name="Nominations", raw_headers=remaining, normalized_headers=remaining,
            header_row_index=1, data_row_count=10,
        )
        issues = validate_mapping_against_inspection(mapping, current)
        errors = [i for i in issues if i.severity == "error"]
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].field, CanonicalField.EMPLOYEE_EMAIL)

    def test_new_unmapped_column_is_a_warning_not_error(self):
        mapping = _sample_mapping()
        current_headers = mapping.raw_headers + ("Manager Email",)
        current = SheetInspection(
            sheet_name="Nominations", raw_headers=current_headers, normalized_headers=current_headers,
            header_row_index=1, data_row_count=10,
        )
        issues = validate_mapping_against_inspection(mapping, current)
        self.assertTrue(all(i.severity == "warning" for i in issues))
        self.assertTrue(any("Manager Email" in i.message for i in issues))


if __name__ == "__main__":
    unittest.main()
