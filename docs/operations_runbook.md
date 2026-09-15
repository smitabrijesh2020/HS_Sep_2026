# Operations Runbook (MVP slice)

## Running locally (once dependencies are installed in an environment with
network access)
```
pip install -e .[dev]
cp .env.example .env
python sample_data/seed_synthetic.py          # or point DATABASE_URL elsewhere
streamlit run app/main.py
pytest
```

## Running the verified slice in a restricted/offline sandbox (as done this session)
```
cd hs-nomination-automation
python3 sample_data/seed_synthetic.py
python3 -m unittest discover -s tests -p "test_*.py"
```
This path uses only the Python standard library (`domain/`, `services/`,
`scheduler/escalation_schedule.py`, `repositories/sqlite_repository.py`)
and does not require Streamlit/SQLAlchemy/Alembic/Pydantic.

## Incident basics
- Communication failures: check `communication_log.error_detail` (already
  sanitized) and `retry_count`; `scheduler/escalation_schedule.py` +
  `services/communication_service.backoff_seconds` govern retry timing.
- Suspected duplicate email: every log row carries a deterministic
  `idempotency_key` - identical (employee, nomination, comm_type,
  template_version, schedule_date) tuples can only reach `Sent` once.
- Audit questions ("who changed this and when"): `audit_log` table /
  Audit history page.

## Known gaps before any production use
See docs/security_privacy_checklist.md and docs/traceability_matrix.md.
Notably: no live Graph sending, no RBAC/login, no Postgres verification,
no confirmed FLARE/SF schema.
