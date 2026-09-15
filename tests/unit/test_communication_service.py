import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from domain.enums import CommunicationStatus, CommunicationType
from services.communication_service import (
    SendResult,
    backoff_seconds,
    build_idempotency_key,
    dispatch,
    has_already_succeeded,
)


class TestIdempotency(unittest.TestCase):
    def test_key_is_deterministic(self):
        k1 = build_idempotency_key("emp1", "nom1", CommunicationType.LAUNCH, "v1", "2026-09-01")
        k2 = build_idempotency_key("emp1", "nom1", CommunicationType.LAUNCH, "v1", "2026-09-01")
        self.assertEqual(k1, k2)

    def test_key_differs_by_comm_type(self):
        k1 = build_idempotency_key("emp1", "nom1", CommunicationType.LAUNCH, "v1", "2026-09-01")
        k2 = build_idempotency_key("emp1", "nom1", CommunicationType.REMINDER_1, "v1", "2026-09-01")
        self.assertNotEqual(k1, k2)

    def test_dry_run_dispatch_does_not_call_send_fn(self):
        called = {"count": 0}

        def send_fn():
            called["count"] += 1
            return SendResult(success=True)

        entry = dispatch(
            "emp1", "nom1", CommunicationType.LAUNCH, "v1", "2026-09-01",
            existing_log=[], send_fn=send_fn, dry_run=True,
        )
        self.assertEqual(entry.status, CommunicationStatus.DRY_RUN)
        self.assertEqual(called["count"], 0)

    def test_duplicate_send_is_suppressed(self):
        key = build_idempotency_key("emp1", "nom1", CommunicationType.LAUNCH, "v1", "2026-09-01")
        already_sent = dispatch(
            "emp1", "nom1", CommunicationType.LAUNCH, "v1", "2026-09-01",
            existing_log=[], send_fn=lambda: SendResult(success=True), dry_run=False,
        )
        # simulate that it actually succeeded previously
        already_sent.status = CommunicationStatus.SENT
        already_sent.idempotency_key = key

        second_attempt = dispatch(
            "emp1", "nom1", CommunicationType.LAUNCH, "v1", "2026-09-01",
            existing_log=[already_sent], send_fn=lambda: SendResult(success=True), dry_run=False,
        )
        self.assertEqual(second_attempt.status, CommunicationStatus.SUPPRESSED)

    def test_overlapping_scheduler_runs_cannot_double_send(self):
        """Simulates two 'overlapping runs' checking the same existing_log
        snapshot after the first one recorded success."""
        log = []
        first = dispatch(
            "emp1", "nom1", CommunicationType.REMINDER_1, "v1", "2026-09-04",
            existing_log=log, send_fn=lambda: SendResult(success=True, provider_message_id="m1"),
            dry_run=False,
        )
        log.append(first)
        second = dispatch(
            "emp1", "nom1", CommunicationType.REMINDER_1, "v1", "2026-09-04",
            existing_log=log, send_fn=lambda: SendResult(success=True, provider_message_id="m2"),
            dry_run=False,
        )
        self.assertEqual(first.status, CommunicationStatus.SENT)
        self.assertEqual(second.status, CommunicationStatus.SUPPRESSED)

    def test_transient_failure_marks_retrying_until_max_retries(self):
        entry = dispatch(
            "emp1", "nom1", CommunicationType.ESCALATION, "v1", "2026-09-08",
            existing_log=[], send_fn=lambda: SendResult(success=False, error="SMTP timeout"),
            dry_run=False, max_retries=3, attempt=1,
        )
        self.assertEqual(entry.status, CommunicationStatus.RETRYING)

    def test_exhausted_retries_marks_failed(self):
        entry = dispatch(
            "emp1", "nom1", CommunicationType.ESCALATION, "v1", "2026-09-08",
            existing_log=[], send_fn=lambda: SendResult(success=False, error="SMTP timeout"),
            dry_run=False, max_retries=3, attempt=3,
        )
        self.assertEqual(entry.status, CommunicationStatus.FAILED)

    def test_error_detail_with_secret_marker_is_sanitized(self):
        entry = dispatch(
            "emp1", "nom1", CommunicationType.LAUNCH, "v1", "2026-09-01",
            existing_log=[], send_fn=lambda: SendResult(success=False, error="Invalid access token: abc123"),
            dry_run=False, max_retries=0, attempt=1,
        )
        self.assertNotIn("abc123", entry.error_detail or "")

    def test_backoff_is_capped(self):
        self.assertLessEqual(backoff_seconds(50), 300.0)


if __name__ == "__main__":
    unittest.main()
