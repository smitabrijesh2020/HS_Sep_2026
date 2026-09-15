"""Integration test: Program -> Batch -> Nomination -> Eligibility ->
Dry-run Communication Log, using the runnable sqlite3 repository. Uses a
temp file DB (never the real hs_nomination.db) and only synthetic data.
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from domain.enums import BatchStatus, CheckSource, CommunicationType, ProgramStatus, RuleResultStatus
from domain.models import AuditLogEntry, Batch, Employee, Program
from repositories.sqlite_repository import SqliteRepository
from services.communication_service import SendResult, dispatch
from services.eligibility_engine import RuleDefinition, decide, evaluate_rules
from services.nomination_service import create_nomination


class TestVerticalSlice(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.tmpdir.name) / "test_slice.db")
        self.repo = SqliteRepository(self.db_path)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_full_slice(self):
        program = Program(name="Synthetic Program", status=ProgramStatus.ACTIVE,
                           created_by="test", updated_by="test")
        self.repo.add_program(program)

        batch = Batch(program_id=program.id, trf_number="T-1", capacity=2,
                       status=BatchStatus.OPEN, created_by="test", updated_by="test")
        self.repo.add_batch(batch)

        employee = Employee(employee_code="SYN-001", display_name="Ava Example", email="ava@example.org")
        self.repo.add_employee(employee)

        existing = self.repo.list_nominations(employee_id=employee.id)
        nomination, audit = create_nomination(existing, employee.id, program.id, batch.id, actor="test")
        self.repo.add_nomination(nomination)
        self.repo.add_audit(audit)

        # Duplicate active nomination must be rejected.
        existing_after = self.repo.list_nominations(employee_id=employee.id)
        with self.assertRaises(Exception):
            create_nomination(existing_after, employee.id, program.id, batch.id, actor="test")

        # Eligibility: all data available and passing -> Eligible
        rules = [
            RuleDefinition("HS Completion", CheckSource.HS_REPORT,
                            lambda c: RuleResultStatus.PASS if c.get("hs_completed") else RuleResultStatus.FAIL),
        ]
        results = evaluate_rules(nomination.id, {"hs_completed": True}, rules)
        decision = decide(nomination.id, results, {r.name: r for r in rules})
        self.repo.add_eligibility_results(results)
        self.repo.add_eligibility_decision(decision)
        self.assertEqual(decision.status.value, "Eligible")

        # Dry-run communication with idempotency
        log_before = self.repo.list_communication_log(nomination.id)
        entry = dispatch(
            employee.id, nomination.id, CommunicationType.LAUNCH, "v1", "2026-09-01",
            existing_log=log_before, send_fn=lambda: SendResult(success=True), dry_run=True,
        )
        self.repo.add_communication_log(entry)
        self.repo.add_audit(AuditLogEntry(entity_type="Communication", entity_id=entry.id,
                                           action=entry.status.value, actor="test", detail="launch dry-run"))

        log_after = self.repo.list_communication_log(nomination.id)
        self.assertEqual(len(log_after), 1)
        self.assertEqual(log_after[0].status.value, "DryRun")

        # Seat utilization reflects the one active nomination
        summary = self.repo.seat_summary(batch.id)
        self.assertEqual(summary["filled"], 1)
        self.assertEqual(summary["available"], 1)

        # Audit trail has at least: nomination created + communication dry-run
        audit_rows = self.repo.list_audit()
        self.assertGreaterEqual(len(audit_rows), 2)


if __name__ == "__main__":
    unittest.main()
