import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from domain.enums import CommunicationType
from scheduler.escalation_schedule import ScheduleConfig, compute_due_date, compute_full_schedule, is_due


class TestEscalationSchedule(unittest.TestCase):
    def test_default_offsets(self):
        launch = date(2026, 9, 1)
        schedule = compute_full_schedule(launch)
        self.assertEqual(schedule[CommunicationType.LAUNCH], date(2026, 9, 1))
        self.assertEqual(schedule[CommunicationType.REMINDER_1], date(2026, 9, 4))
        self.assertEqual(schedule[CommunicationType.REMINDER_2], date(2026, 9, 6))
        self.assertEqual(schedule[CommunicationType.ESCALATION], date(2026, 9, 8))
        self.assertEqual(schedule[CommunicationType.FINAL_REMINDER], date(2026, 9, 10))
        self.assertEqual(schedule[CommunicationType.CLOSURE_REVIEW], date(2026, 9, 12))

    def test_is_due_true_on_and_after_due_date(self):
        launch = date(2026, 9, 1)
        self.assertFalse(is_due(CommunicationType.REMINDER_1, launch, date(2026, 9, 3)))
        self.assertTrue(is_due(CommunicationType.REMINDER_1, launch, date(2026, 9, 4)))
        self.assertTrue(is_due(CommunicationType.REMINDER_1, launch, date(2026, 9, 5)))

    def test_business_days_only_skips_weekends(self):
        # 2026-09-01 is a Tuesday. +3 business days -> Fri 2026-09-04 (no weekend in range).
        launch = date(2026, 9, 1)
        config = ScheduleConfig(business_days_only=True)
        due = compute_due_date(launch, CommunicationType.REMINDER_1, config)
        self.assertEqual(due.weekday(), 4)  # Friday
        self.assertEqual(due, date(2026, 9, 4))

    def test_business_days_only_over_a_weekend(self):
        # Launch on Thursday 2026-09-03; +3 business days must skip Sat/Sun.
        launch = date(2026, 9, 3)
        config = ScheduleConfig(business_days_only=True)
        due = compute_due_date(launch, CommunicationType.REMINDER_1, config)
        # Thu -> Fri(1) -> Mon(2) -> Tue(3)
        self.assertEqual(due, date(2026, 9, 8))

    def test_unknown_comm_type_raises(self):
        config = ScheduleConfig(offsets={})
        with self.assertRaises(ValueError):
            compute_due_date(date(2026, 9, 1), CommunicationType.LAUNCH, config)


if __name__ == "__main__":
    unittest.main()
