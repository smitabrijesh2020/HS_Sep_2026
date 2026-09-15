"""Unit tests for services.workbook_inspector.

All fixtures use synthetic values in real-shaped headers - never real
employee data (see docs/security_privacy_checklist.md and lesson.md).
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from domain.mapping_models import SourceKind
from services.workbook_inspector import (
    inspect_workbook,
    list_source_files,
    read_sheet_rows,
    suggest_classification,
)
from tests.fixtures.synthetic_workbook_builder import (
    HS_REPORT_HEADERS,
    IMOCHA_REPORT_HEADERS,
    NOMINATION_TRACKER_HEADERS,
    build_workbook,
)


class TestListSourceFiles(unittest.TestCase):
    def test_classifies_by_extension_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            build_workbook(folder / "tracker.xlsx", {"Sheet1": [["A", "B"], [1, 2]]})
            (folder / "welcome_mailer.msg").write_bytes(b"not a real msg file")
            (folder / "notes.txt").write_text("scratch notes")

            files = {Path(f.file_path).name: f for f in list_source_files(folder)}

            self.assertTrue(files["tracker.xlsx"].is_supported)
            self.assertFalse(files["welcome_mailer.msg"].is_supported)
            self.assertIsNotNone(files["welcome_mailer.msg"].skip_reason)
            self.assertFalse(files["notes.txt"].is_supported)

    def test_missing_folder_raises_clear_error(self):
        with self.assertRaises(FileNotFoundError):
            list_source_files(Path("Z:/definitely/does/not/exist"))


class TestInspectWorkbook(unittest.TestCase):
    def test_nomination_tracker_shaped_sheet_is_read_correctly(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = build_workbook(
                Path(tmp) / "nominations.xlsx",
                {"Nominations": [
                    NOMINATION_TRACKER_HEADERS,
                    [100234, "Test Employee One", "test1@example.org", "AWS Cert", "TRF-1", "Cleared"],
                ]},
            )
            result = inspect_workbook(path)
            self.assertIsNone(result.open_error)
            self.assertEqual([s.sheet_name for s in result.sheets], ["Nominations"])
            self.assertEqual(result.sheets[0].normalized_headers, tuple(NOMINATION_TRACKER_HEADERS))
            self.assertEqual(result.sheets[0].data_row_count, 1)

    def test_trailing_whitespace_headers_are_normalized(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = build_workbook(
                Path(tmp) / "imocha.xlsx",
                {"Test Level Report": [IMOCHA_REPORT_HEADERS]},
            )
            result = inspect_workbook(path)
            self.assertIn("Total_Questions", result.sheets[0].normalized_headers)
            self.assertNotIn("Total_Questions ", result.sheets[0].normalized_headers)

    def test_missing_file_reports_sanitized_open_error_not_raise(self):
        result = inspect_workbook(Path("Z:/nope/definitely_missing.xlsx"))
        self.assertIsNotNone(result.open_error)
        self.assertEqual(result.sheets, ())

    def test_corrupted_file_reports_open_error_not_raise(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "corrupted.xlsx"
            path.write_bytes(b"this is not a valid xlsx file at all")
            result = inspect_workbook(path)
            self.assertIsNotNone(result.open_error)

    def test_blank_header_row_is_flagged_not_raised(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = build_workbook(Path(tmp) / "empty.xlsx", {"Sheet1": []})
            result = inspect_workbook(path)
            self.assertIsNone(result.open_error)
            self.assertIsNotNone(result.sheets[0].sample_issue)


class TestSuggestClassification(unittest.TestCase):
    def test_nomination_tracker_headers_are_recognized(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = build_workbook(Path(tmp) / "f.xlsx", {"Nominations": [NOMINATION_TRACKER_HEADERS]})
            suggestion = suggest_classification(inspect_workbook(path).sheets[0])
            self.assertEqual(suggestion.source_kind, SourceKind.NOMINATION_TRACKER)

    def test_hs_report_headers_are_recognized(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = build_workbook(Path(tmp) / "f.xlsx", {"Data": [HS_REPORT_HEADERS]})
            suggestion = suggest_classification(inspect_workbook(path).sheets[0])
            self.assertEqual(suggestion.source_kind, SourceKind.HS_REPORT)

    def test_imocha_headers_are_recognized(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = build_workbook(Path(tmp) / "f.xlsx", {"Test Level Report": [IMOCHA_REPORT_HEADERS]})
            suggestion = suggest_classification(inspect_workbook(path).sheets[0])
            self.assertEqual(suggestion.source_kind, SourceKind.IMOCHA_REPORT)

    def test_unrelated_headers_are_unknown_not_guessed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = build_workbook(
                Path(tmp) / "f.xlsx", {"Sheet1": [["Favorite Color", "Shoe Size", "Lucky Number"]]}
            )
            suggestion = suggest_classification(inspect_workbook(path).sheets[0])
            self.assertEqual(suggestion.source_kind, SourceKind.UNKNOWN)


class TestReadSheetRows(unittest.TestCase):
    def test_reads_rows_keyed_by_normalized_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = build_workbook(
                Path(tmp) / "f.xlsx",
                {"Nominations": [
                    NOMINATION_TRACKER_HEADERS,
                    [100234, "Test Employee One", "test1@example.org", "AWS Cert", "TRF-1", "Cleared"],
                    [100235, "Test Employee Two", "test2@example.org", "AWS Cert", "TRF-1", ""],
                ]},
            )
            rows = read_sheet_rows(path, "Nominations")
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["Emp ID"], 100234)
            self.assertEqual(rows[0]["Email"], "test1@example.org")

    def test_fully_blank_trailing_rows_are_dropped(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = build_workbook(
                Path(tmp) / "f.xlsx",
                {"Nominations": [
                    NOMINATION_TRACKER_HEADERS,
                    [100234, "Test Employee One", "test1@example.org", "AWS Cert", "TRF-1", "Cleared"],
                    [None, None, None, None, None, None],
                ]},
            )
            rows = read_sheet_rows(path, "Nominations")
            self.assertEqual(len(rows), 1)


if __name__ == "__main__":
    unittest.main()
