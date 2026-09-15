# Assumptions and Decision Log

| # | Decision / Assumption | Rationale | Status |
|---|---|---|---|
| 1 | Persistence target = SQLAlchemy + SQLite (not PostgreSQL) | Explicit user choice when asked about the Dataverse-vs-brief conflict | Confirmed by user |
| 2 | Python 3.10 used to author/run this session (pyproject pins >=3.12) | Sandbox ships Python 3.10; brief requests 3.12+. No functionality in this slice is 3.12-specific. | Assumption - revisit target runtime with the deployment owner |
| 3 | SQLAlchemy/Alembic/Pydantic/Streamlit not executed this session | No outbound network access in sandbox (pip 403) | Documented limitation, not a design gap |
| 4 | Real employee data in the folder (Nominations, Certifications, BAU Test Report, Registration Form trackers) was inspected only for schema/structure, never copied into code, tests, or seed data | Security/privacy requirement: synthetic data only in dev/test | Followed |
| 5 | FLARE and SF target schemas are unknown | No mapping spec was supplied | Flagged - export module ships a labeled, editable template only; do not use for a real submission until confirmed |
| 6 | Microsoft Graph integration ships in dry-run-only mode; no MSAL wiring against a real tenant | Project rule: never send real email / never touch production systems without approval | By design - `GraphAuthenticator.acquire_token()` raises if `dry_run=False` |
| 7 | Retention periods in `.env.example` (365 days) are placeholders | Project rule: do not invent org retention policy | Needs Data Privacy Officer sign-off before use |
| 8 | Duplicate-active-nomination prevention enforced in the service layer (Python) plus, for Postgres only, a partial unique index in the Alembic migration | SQLite's DDL dialect doesn't support the same partial-index syntax portably; the application-level check is authoritative in the SQLite MVP | Implemented and tested (service layer) / designed only (Postgres partial index) |
| 9 | This session's scope is the single vertical slice named in the brief (Program -> Batch -> Nomination -> Eligibility -> Dry-run Communication Log), not the full 16-item deliverable list | Working method requires the smallest coherent slice first | Deliberate scope limit - see docs/traceability_matrix.md for what's outstanding |
