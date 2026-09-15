"""Unit tests for services.employee_matching_service.

Scenarios mirror masterprompt.md's own TESTING section (items 5-8):
duplicate EmployeeID, ID stored as a decimal, email-only match, and
multiple probable name matches. All values are fabricated.
"""
from __future__ import annotations

import unittest

from domain.models import Employee
from services.employee_matching_service import (
    MatchStatus,
    RegistrationAction,
    build_employee_index,
    match_employee,
    resolve_or_flag_new_employee,
)


def _employee(code: str, name: str, email: str) -> Employee:
    return Employee(employee_code=code, display_name=name, email=email)


class TestMatchEmployee(unittest.TestCase):
    def setUp(self):
        self.alice = _employee("100234", "Alice Example", "alice.example@example.org")
        self.bob = _employee("100235", "Bob Example", "bob.example@example.org")
        self.index = build_employee_index([self.alice, self.bob])

    def test_exact_match_by_employee_id(self):
        result = match_employee("100234", None, None, self.index)
        self.assertEqual(result.status, MatchStatus.EXACT_MATCH)
        self.assertEqual(result.employee_id, self.alice.id)
        self.assertEqual(result.matched_on, "EmployeeID")

    def test_employee_id_stored_as_decimal_still_matches(self):
        result = match_employee(100234.0, None, None, self.index)
        self.assertEqual(result.status, MatchStatus.EXACT_MATCH)
        self.assertEqual(result.employee_id, self.alice.id)

    def test_match_by_email_only_when_id_unavailable(self):
        result = match_employee(None, "ALICE.EXAMPLE@EXAMPLE.ORG", None, self.index)
        self.assertEqual(result.status, MatchStatus.EXACT_MATCH)
        self.assertEqual(result.employee_id, self.alice.id)
        self.assertEqual(result.matched_on, "Email")

    def test_id_takes_priority_over_email(self):
        # Email belongs to Bob, but ID belongs to Alice - ID must win per priority order.
        result = match_employee("100234", "bob.example@example.org", None, self.index)
        self.assertEqual(result.employee_id, self.alice.id)
        self.assertEqual(result.matched_on, "EmployeeID")

    def test_multiple_employees_sharing_exact_name(self):
        dup_alice = _employee("999999", "Alice Example", "alice.duplicate@example.org")
        index = build_employee_index([self.alice, self.bob, dup_alice])
        result = match_employee(None, None, "Alice Example", index)
        self.assertEqual(result.status, MatchStatus.MULTIPLE_MATCHES)
        self.assertIsNone(result.employee_id)
        self.assertEqual(len(result.candidates), 2)

    def test_no_match_found(self):
        result = match_employee("000000", "nobody@example.org", "Nobody Here", self.index)
        self.assertEqual(result.status, MatchStatus.NO_MATCH)

    def test_blank_row_is_invalid_source_record(self):
        result = match_employee(None, None, None, self.index)
        self.assertEqual(result.status, MatchStatus.INVALID_SOURCE_RECORD)

    def test_near_miss_name_is_probable_match_never_auto_elevated(self):
        result = match_employee(None, None, "Alise Example", self.index)  # one-letter typo
        self.assertEqual(result.status, MatchStatus.PROBABLE_MATCH_REVIEW_REQUIRED)
        self.assertNotEqual(result.status, MatchStatus.EXACT_MATCH)

    def test_dissimilar_name_does_not_trigger_fuzzy_match(self):
        result = match_employee(None, None, "Zzz Completely Different", self.index)
        self.assertEqual(result.status, MatchStatus.NO_MATCH)


class TestResolveOrFlagNewEmployee(unittest.TestCase):
    def setUp(self):
        self.alice = _employee("100234", "Alice Example", "alice.example@example.org")
        self.index = build_employee_index([self.alice])

    def test_known_id_reuses_existing_employee(self):
        result = resolve_or_flag_new_employee("100234", "Alice Example", "alice.example@example.org", self.index)
        self.assertEqual(result.action, RegistrationAction.USE_EXISTING)
        self.assertEqual(result.employee_id, self.alice.id)

    def test_new_id_flags_create_new(self):
        result = resolve_or_flag_new_employee("555555", "New Employee", "new.employee@example.org", self.index)
        self.assertEqual(result.action, RegistrationAction.CREATE_NEW)
        self.assertIsNone(result.employee_id)

    def test_blank_id_and_blank_email_is_invalid_record(self):
        result = resolve_or_flag_new_employee(None, "Someone", None, self.index)
        self.assertEqual(result.action, RegistrationAction.INVALID_RECORD)

    def test_duplicate_employee_id_in_two_rows_both_resolve_to_same_existing_employee(self):
        first = resolve_or_flag_new_employee("100234", "Alice Example", "alice.example@example.org", self.index)
        second = resolve_or_flag_new_employee("100234", "Alice Example", "alice.example@example.org", self.index)
        self.assertEqual(first.action, RegistrationAction.USE_EXISTING)
        self.assertEqual(second.action, RegistrationAction.USE_EXISTING)
        self.assertEqual(first.employee_id, second.employee_id)

    def test_blank_id_matched_by_email_reuses_existing_employee(self):
        result = resolve_or_flag_new_employee(None, "Alice Example", "alice.example@example.org", self.index)
        self.assertEqual(result.action, RegistrationAction.USE_EXISTING)
        self.assertEqual(result.employee_id, self.alice.id)

    def test_blank_id_unmatched_email_requires_manual_code(self):
        result = resolve_or_flag_new_employee(None, "Nobody", "nobody@example.org", self.index)
        self.assertEqual(result.action, RegistrationAction.MANUAL_CODE_REQUIRED)

    def test_id_matches_one_employee_but_email_matches_another_is_conflict(self):
        bob = _employee("999999", "Bob Example", "bob.example@example.org")
        index = build_employee_index([self.alice, bob])
        # Row claims Alice's ID but Bob's email.
        result = resolve_or_flag_new_employee("100234", "Alice Example", "bob.example@example.org", index)
        self.assertEqual(result.action, RegistrationAction.CONFLICT_REVIEW_REQUIRED)


if __name__ == "__main__":
    unittest.main()
