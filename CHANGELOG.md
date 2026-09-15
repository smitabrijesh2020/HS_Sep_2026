# Changelog

## 2026-09-01 - Initial vertical slice
- Audited the "HS Automation" folder (no existing app code found; business
  docs and trackers only).
- Resolved architecture fork (Dataverse doc vs. brief default) with user:
  built on SQLAlchemy + SQLite, Streamlit UI.
- Implemented domain models, nomination dedup service, eligibility engine
  (with missing-data-safe decisioning and manual overrides), dry-run
  communication service with idempotency, escalation date calculator.
- Implemented a runnable stdlib-`sqlite3` repository (network-restricted
  sandbox could not install SQLAlchemy/Alembic/Pydantic/Streamlit) plus the
  target SQLAlchemy ORM models, Alembic migration, and Streamlit UI written
  to spec but unverified.
- Added FLARE/SF export mapping template (schema unknown - flagged for review).
- Added Power BI view SQL and DAX measure notes (designed only).
- Added synthetic seed data and 33 automated tests (all passing).
- Added architecture, assumptions/decision log, security/privacy checklist,
  operations runbook, and traceability matrix docs.
