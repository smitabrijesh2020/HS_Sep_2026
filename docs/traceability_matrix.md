# Traceability Matrix (this session's scope only)

Legend: **Tested** = implemented + passing automated tests this session.
**Unverified** = written to spec, not executed (sandbox had no package-index
access). **Designed** = spec/document only, no code. **Deferred** = not
started, in scope for a later increment.

| Requirement | Implementation | Status |
|---|---|---|
| Program CRUD + status | `domain/models.Program`, `repositories/sqlite_repository.py`, `app/ui/programs_page.py` | Tested (repo/service) / Unverified (Streamlit UI) |
| Batch CRUD + seat utilization | `domain/models.Batch`, `SqliteRepository.seat_summary`, `app/ui/batches_page.py` | Tested (repo) / Unverified (UI) |
| Prevent duplicate active nominations | `services/nomination_service.py` | **Tested** (7 unit tests) |
| Nomination status lifecycle | `domain/enums.NominationStatus`, `transition_status` | **Tested** |
| Eligibility rule-by-rule results + overall decision | `services/eligibility_engine.py` | **Tested** (7 unit tests incl. missing-data path) |
| Missing data never causes automatic adverse decision | `RuleResultStatus.DATA_UNAVAILABLE` handling in `decide()` | **Tested** explicitly |
| Manual override with actor/reason/timestamp | `apply_manual_override` | **Tested** |
| Communication idempotency / duplicate suppression | `services/communication_service.py` | **Tested** (8 unit tests incl. simulated overlapping runs) |
| Retry with exponential backoff | `backoff_seconds`, `RETRYING`/`FAILED` states | **Tested** |
| Sanitized error logging | `_sanitize_error` | **Tested** |
| Escalation day 0/3/5/7/9/11 schedule | `scheduler/escalation_schedule.py` | **Tested** (5 unit tests incl. business-day rule) |
| End-to-end slice (Program->Batch->Nomination->Eligibility->Dry-run comm log) | `tests/integration/test_vertical_slice_end_to_end.py` | **Tested** |
| SQLAlchemy ORM schema (target ) | `repositories/orm_models.py` | Unverified |
| Alembic migration | `migrations/` | Unverified |
| Pydantic settings | `config/settings.py` | Unverified |
| Streamlit pages (Programs/Batches/Nominations/Eligibility/Communications/Audit) | `app/main.py`, `app/ui/*.py` | Unverified |
| Microsoft Graph dry-run abstraction | `integrations/graph_client.py` | Unverified (syntax-checked; no live call) |
| FLARE/SF export mapping template | `exports/flare_sf_export.py` | **Tested** (validation logic only; target schema still unknown - Designed/flagged) |
| Power BI views + DAX measures | `reporting/powerbi_views.sql`, `reporting/dax_measures.md` | Designed only |
| Login/identity, Exports UI, Administration pages | - | **Deferred** |
| Users/Roles/RBAC enforcement | `orm_models.User`/`Role` tables exist; no enforcement logic | Designed only |
| Communication templates (configurable HTML/text) | - | **Deferred** |
| Audit log UI | `app/ui/audit_page.py` | Unverified (UI) / underlying `audit_log` writes are Tested |

## Test run evidence (this session)
`python3 -m unittest discover -s tests -p "test_*.py"` -> **33 tests, all passing**.
`python3 -m py_compile` on every non-test `.py` file -> all syntactically valid.
