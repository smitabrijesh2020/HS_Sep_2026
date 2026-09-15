"""Generate synthetic (fake) sample data for the MVP slice.

CRITICAL: this script must never be pointed at real HR/HS exports. All
names, emails, and employee codes below are fabricated. Real employee data
must not be used in dev/test per project security rules.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from domain.enums import BatchStatus, ProgramStatus
from domain.models import Batch, Employee, Program
from repositories.sqlite_repository import SqliteRepository

SYNTHETIC_EMPLOYEES = [
    ("SYN-001", "Ava Example", "ava.example@example.org"),
    ("SYN-002", "Ben Example", "ben.example@example.org"),
    ("SYN-003", "Cora Example", "cora.example@example.org"),
    ("SYN-004", "Dev Example", "dev.example@example.org"),
    ("SYN-005", "Ela Example", "ela.example@example.org"),
]


def seed(db_path: str = "hs_nomination.db") -> SqliteRepository:
    repo = SqliteRepository(db_path)

    program = Program(
        name="AWS Certified Solutions Architect - Associate Readiness",
        description="Synthetic sample program for demo purposes only.",
        owner="demo-owner@example.org",
        business_unit="Demo-BU",
        technology="AWS",
        status=ProgramStatus.ACTIVE,
        created_by="seed_script",
        updated_by="seed_script",
    )
    repo.add_program(program)

    batch = Batch(
        program_id=program.id,
        trf_number="DEMO_AWS_202609_1",
        capacity=3,
        trainer="Synthetic Trainer",
        location="Virtual",
        delivery_mode="Virtual",
        status=BatchStatus.OPEN,
        created_by="seed_script",
        updated_by="seed_script",
    )
    repo.add_batch(batch)

    for code, name, email in SYNTHETIC_EMPLOYEES:
        repo.add_employee(Employee(employee_code=code, display_name=name, email=email))

    print(f"Seeded program={program.id} batch={batch.id} with {len(SYNTHETIC_EMPLOYEES)} synthetic employees.")
    return repo


if __name__ == "__main__":
    seed()
