import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from domain.enums import NominationStatus
from domain.models import Nomination
from services.nomination_service import (
    DuplicateActiveNominationError,
    create_nomination,
    find_duplicate_active_nomination,
    transition_status,
)


class TestDuplicatePrevention(unittest.TestCase):
    def test_no_duplicate_when_no_existing_nominations(self):
        dup = find_duplicate_active_nomination([], "emp1", "prog1", "batch1")
        self.assertIsNone(dup)

    def test_detects_active_duplicate(self):
        existing = [Nomination(employee_id="emp1", program_id="prog1", batch_id="batch1",
                                status=NominationStatus.SUBMITTED)]
        dup = find_duplicate_active_nomination(existing, "emp1", "prog1", "batch1")
        self.assertIsNotNone(dup)

    def test_withdrawn_nomination_is_not_a_duplicate(self):
        existing = [Nomination(employee_id="emp1", program_id="prog1", batch_id="batch1",
                                status=NominationStatus.WITHDRAWN)]
        dup = find_duplicate_active_nomination(existing, "emp1", "prog1", "batch1")
        self.assertIsNone(dup)

    def test_different_batch_is_not_a_duplicate(self):
        existing = [Nomination(employee_id="emp1", program_id="prog1", batch_id="batch1",
                                status=NominationStatus.CONFIRMED)]
        dup = find_duplicate_active_nomination(existing, "emp1", "prog1", "batch2")
        self.assertIsNone(dup)

    def test_create_nomination_raises_on_duplicate(self):
        existing = [Nomination(employee_id="emp1", program_id="prog1", batch_id="batch1",
                                status=NominationStatus.ELIGIBLE)]
        with self.assertRaises(DuplicateActiveNominationError):
            create_nomination(existing, "emp1", "prog1", "batch1", actor="tester")

    def test_create_nomination_succeeds_when_no_duplicate(self):
        nomination, audit = create_nomination([], "emp1", "prog1", "batch1", actor="tester")
        self.assertEqual(nomination.status, NominationStatus.SUBMITTED)
        self.assertEqual(audit.action, "Created")

    def test_archived_duplicate_is_ignored(self):
        existing = [Nomination(employee_id="emp1", program_id="prog1", batch_id="batch1",
                                status=NominationStatus.SUBMITTED, is_archived=True)]
        dup = find_duplicate_active_nomination(existing, "emp1", "prog1", "batch1")
        self.assertIsNone(dup)

    def test_transition_status_produces_audit_entry(self):
        nomination = Nomination(employee_id="emp1", program_id="prog1", batch_id="batch1",
                                 status=NominationStatus.SUBMITTED)
        updated, audit = transition_status(nomination, NominationStatus.CONFIRMED, "tester", "manual review passed")
        self.assertEqual(updated.status, NominationStatus.CONFIRMED)
        self.assertIn("Submitted -> Confirmed", audit.detail)


if __name__ == "__main__":
    unittest.main()
