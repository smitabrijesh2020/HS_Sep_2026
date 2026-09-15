"""Unit tests for utils.normalizers.

Every case here is drawn from real, session-observed shapes (trailing-space
headers, decimal-stored IDs, a non-breaking-space filename) but uses only
fabricated values - never real employee data.
"""
from __future__ import annotations

import unittest
from datetime import datetime

from utils.normalizers import (
    BLANK_MARKERS,
    is_blank,
    is_valid_email_shape,
    normalize_email,
    normalize_employee_id,
    normalize_header_key,
    normalize_header_name,
    normalize_name,
    normalize_name_for_matching,
    normalize_status_text,
    normalize_whitespace,
    parse_flexible_date,
)


class TestNormalizeWhitespace(unittest.TestCase):
    def test_none_is_empty_string(self):
        self.assertEqual(normalize_whitespace(None), "")

    def test_nan_is_empty_string(self):
        self.assertEqual(normalize_whitespace(float("nan")), "")

    def test_trailing_space_header_is_trimmed(self):
        # Real header observed this session: "Total_Questions "
        self.assertEqual(normalize_whitespace("Total_Questions "), "Total_Questions")

    def test_trailing_space_before_unit_suffix_is_trimmed(self):
        # Real header observed this session: "Email Id "
        self.assertEqual(normalize_whitespace("Email Id "), "Email Id")

    def test_non_breaking_space_is_collapsed(self):
        # The exact character shape that blocked opening a real workbook this session.
        self.assertEqual(normalize_whitespace("Registration\xa0Form"), "Registration Form")

    def test_internal_double_space_is_collapsed(self):
        self.assertEqual(normalize_whitespace("Test  Employee   Name"), "Test Employee Name")


class TestHeaderNormalizers(unittest.TestCase):
    def test_header_name_matches_whitespace_normalize(self):
        self.assertEqual(normalize_header_name("Total_Questions "), "Total_Questions")

    def test_header_key_loosely_matches_across_naming_styles(self):
        # 'Emp ID' ~ 'EMPLID' ~ 'Employee_ID' should collapse to a comparable key.
        self.assertEqual(normalize_header_key("Emp ID"), normalize_header_key("EMP ID"))
        self.assertNotEqual(normalize_header_key("Emp ID"), normalize_header_key("EMPLID"))


class TestNormalizeEmployeeId(unittest.TestCase):
    def test_none_is_empty_string(self):
        self.assertEqual(normalize_employee_id(None), "")

    def test_int_and_decimal_float_and_string_all_match(self):
        # The exact "decimal-stored employee ID" problem named in the brief.
        self.assertEqual(normalize_employee_id(100234), "100234")
        self.assertEqual(normalize_employee_id(100234.0), "100234")
        self.assertEqual(normalize_employee_id("100234"), "100234")
        self.assertEqual(
            normalize_employee_id(100234),
            normalize_employee_id(100234.0),
        )

    def test_nan_float_is_empty_string(self):
        self.assertEqual(normalize_employee_id(float("nan")), "")

    def test_string_with_whitespace_is_trimmed(self):
        self.assertEqual(normalize_employee_id("  100234  "), "100234")


class TestNormalizeEmail(unittest.TestCase):
    def test_case_is_folded(self):
        self.assertEqual(normalize_email("Test.Employee@Example.ORG"), "test.employee@example.org")

    def test_none_is_empty_string(self):
        self.assertEqual(normalize_email(None), "")

    def test_whitespace_is_trimmed(self):
        self.assertEqual(normalize_email(" test1@example.org "), "test1@example.org")


class TestIsValidEmailShape(unittest.TestCase):
    def test_plausible_email_is_valid(self):
        self.assertTrue(is_valid_email_shape("test1@example.org"))

    def test_missing_at_is_invalid(self):
        self.assertFalse(is_valid_email_shape("test1example.org"))

    def test_missing_domain_dot_is_invalid(self):
        self.assertFalse(is_valid_email_shape("test1@example"))

    def test_multiple_at_signs_is_invalid(self):
        self.assertFalse(is_valid_email_shape("test1@@example.org"))


class TestNormalizeName(unittest.TestCase):
    def test_case_is_preserved_for_display(self):
        self.assertEqual(normalize_name("Test Employee"), "Test Employee")

    def test_matching_form_is_case_folded(self):
        self.assertEqual(normalize_name_for_matching("Test Employee"), "test employee")
        self.assertEqual(
            normalize_name_for_matching("TEST EMPLOYEE"),
            normalize_name_for_matching("test employee"),
        )


class TestIsBlank(unittest.TestCase):
    def test_none_is_blank(self):
        self.assertTrue(is_blank(None))

    def test_empty_string_is_blank(self):
        self.assertTrue(is_blank(""))

    def test_every_blank_marker_is_recognized(self):
        for marker in BLANK_MARKERS:
            if marker == "":
                continue
            with self.subTest(marker=marker):
                self.assertTrue(is_blank(marker))
                self.assertTrue(is_blank(marker.upper()))

    def test_real_value_is_not_blank(self):
        self.assertFalse(is_blank("Completed"))


class TestNormalizeStatusText(unittest.TestCase):
    def test_case_and_whitespace_variance_collapse(self):
        self.assertEqual(normalize_status_text(" Completed "), "completed")
        self.assertEqual(normalize_status_text("COMPLETED"), normalize_status_text("completed"))


class TestParseFlexibleDate(unittest.TestCase):
    def test_none_returns_none(self):
        self.assertIsNone(parse_flexible_date(None))

    def test_garbage_string_returns_none_not_raise(self):
        self.assertIsNone(parse_flexible_date("not a date"))

    def test_datetime_passthrough(self):
        dt = datetime(2026, 3, 4)
        self.assertEqual(parse_flexible_date(dt), dt)

    def test_iso_date_string(self):
        self.assertEqual(parse_flexible_date("2026-03-04"), datetime(2026, 3, 4))

    def test_day_month_name_year(self):
        self.assertEqual(parse_flexible_date("04-Mar-2026"), datetime(2026, 3, 4))

    def test_day_month_name_year_with_time(self):
        # Shape observed in a real column this session (values fabricated).
        self.assertEqual(
            parse_flexible_date("04-Mar-2026 11:04 PM"),
            datetime(2026, 3, 4, 23, 4),
        )

    def test_slash_date_ambiguous_format_is_parsed_as_day_month_year_first(self):
        self.assertEqual(parse_flexible_date("04/03/2026"), datetime(2026, 3, 4))


if __name__ == "__main__":
    unittest.main()
