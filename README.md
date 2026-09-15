# HS Nomination Automation

Lifecycle management for learning-program nominations: programs, batches,
nominations, eligibility validation, dry-run communications, and (in later
increments) escalation scheduling, exports, and Power BI reporting.

**Current scope (this session):** a single vertical slice — Program ->
Batch -> Nomination -> Eligibility Result -> Dry-run Communication Log —
plus supporting docs. See `docs/traceability_matrix.md` for exactly what's
tested vs. designed-only, and `docs/assumptions_and_decision_log.md` for
key decisions.

## Quick start (environment with network access)
```
pip install -e .[dev]
cp .env.example .env
python sample_data/seed_synthetic.py
streamlit run app/main.py
pytest
```

## Quick start (offline / restricted sandbox, stdlib-only path)
```
python3 sample_data/seed_synthetic.py
python3 -m unittest discover -s tests -p "test_*.py"
```

## Layout
```
app/ui/          Streamlit pages
domain/          Framework-agnostic entities and enums
services/        Business logic (dedup, eligibility engine, comms, no I/O)
repositories/    Persistence: sqlite_repository.py (runnable) + orm_models.py (target/Postgres-ready)
integrations/    Microsoft Graph abstraction (dry-run only)
scheduler/       Escalation date math
exports/         FLARE/SF mapping template (schema not yet confirmed)
reporting/       Power BI view SQL + DAX measure notes
migrations/      Alembic (unverified this session)
sample_data/     Synthetic seed data generator - never real employee data
tests/           unit/ + integration/
docs/            architecture, assumptions, security checklist, runbook, traceability matrix
```

## Security note
Do not point `sample_data/seed_synthetic.py` or any test at real employee
exports. Use synthetic data only until a privacy review and RBAC layer are
in place - see `docs/security_privacy_checklist.md`.
