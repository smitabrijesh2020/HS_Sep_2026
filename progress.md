# Progress vs. Master Prompt

Snapshot date: 2026-09-15. Compares the actual repo state against the full
scope in [masterprompt.md](masterprompt.md). This file tracks status only -
for *why* decisions were made, see `docs/assumptions_and_decision_log.md`;
for requirement-level test evidence, see `docs/traceability_matrix.md`.

## Headline

A prior session deliberately built **one vertical slice** end-to-end
(Program -> Batch -> Nomination -> Eligibility Result -> Dry-run
Communication Log) rather than the full 21-activity, 16-screen application
described in the master prompt. That was a documented scope decision, not an
oversight (`docs/assumptions_and_decision_log.md`, decision #9). Everything
below measures against the *full* master prompt, so most rows are
"Not started" by design, not by failure.

## Delivery sequence (Part 1-7 from masterprompt.md)

| Part | Content | Status |
|---|---|---|
| 1 | Assumptions, unresolved inputs, architecture, security model, project structure | Done - `docs/architecture_overview.md`, `docs/assumptions_and_decision_log.md`, `docs/security_privacy_checklist.md` |
| 2 | requirements.txt, .env.example, .gitignore, config files, install instructions | Partial - project uses `pyproject.toml` instead of `requirements.txt`; `.env.example` exists; `.gitignore` added 2026-09-15 (project-level, not repo-root); no `config/*.example.json` files as specified |
| 3 | Models, normalizers, validators, repositories, auth service, SharePoint/local file services | Partial - `domain/models.py`, `domain/enums.py`, `repositories/sqlite_repository.py` + `orm_models.py` exist and the repository layer is tested. No dedicated `auth_service.py`/`sharepoint_service.py`/`local_file_service.py` - only a dry-run `integrations/graph_client.py` |
| 4 | Workbook inspector, nomination service, eligibility engine, delta service, report service, communication service, PPT service | Partial - `services/nomination_service.py`, `services/eligibility_engine.py`, `services/communication_service.py` are tested. No workbook inspector, no delta service, no report service, no PPT service |
| 5 | Complete Tkinter UI, background tasks, navigation, grids, filtering, progress reporting, confirmation dialogs | **Not started as specified** - UI exists but is Streamlit, not Tkinter/ttk. Only 6 of 16 required screens have any equivalent (Programs, Batches, Nominations, Eligibility, Communications, Audit). No worker-thread/queue pattern (not applicable to Streamlit's execution model) |
| 6 | Office Scripts, Power Automate build guides, field mappings, expressions, testing guidance | Not started - no `office_scripts/` or `power_automate/` folders yet |
| 7 | Unit tests, synthetic demo data, UAT, deployment instructions, troubleshooting guide | Partial - 33 unit/integration tests passing, `sample_data/seed_synthetic.py` generates synthetic demo data. No UAT script, no deployment instructions, no troubleshooting guide |

## What is solid today (tested, per docs/traceability_matrix.md)

- Program/Batch CRUD and seat-utilization math (repository layer)
- Duplicate-active-nomination prevention
- Nomination status lifecycle
- Eligibility rule-by-rule engine, including the rule that missing data
  never causes an automatic adverse decision
- Manual eligibility override with actor/reason/timestamp
- Communication idempotency, duplicate suppression, retry with backoff,
  sanitized error logging
- Escalation day 0/3/5/7/9/11 scheduling
- End-to-end integration test across the full vertical slice
- 33/33 automated tests passing as of the last session that ran them

## Explicitly not built yet (full list)

- Tkinter/ttk desktop UI (current UI is Streamlit - unresolved conflict,
  see [memory.md](memory.md))
- MSAL / live Microsoft Graph authentication (dry-run only today)
- SharePoint Live Mode (folder listing, download/upload, source discovery)
- Local Sync Mode file-freshness detection against the real OneDrive folder
- Column Mapping screen
- HS Report / Do-select / iMocha matching against real reports (schemas
  not yet confirmed against real files)
- Delta and Exceptions screen/service
- Reminder Centre and the 12 communication templates (only a dry-run send
  path with idempotency exists)
- Nomination form (Microsoft Forms link storage or internal Tkinter entry
  form)
- PPT generation service
- All 11 report types
- FLARE/SuccessFactors export (a template-only, schema-unconfirmed stub
  exists - `exports/flare_sf_export.py`)
- All 6 Power Automate flows and their build guides
- All 6 Office Scripts
- RBAC / login / identity, encryption at rest, DPIA/privacy review sign-off

## This session's activity (2026-09-15, PR/commit work)

1. Investigated the repo before touching anything: the project folder was
   entirely untracked (never committed).
2. Found and excluded the real business data files sitting next to the
   project (nomination/certification workbooks, `.msg` exports) - not
   committed.
3. Added `.gitignore` (none existed); confirmed no hardcoded secrets in
   source before pushing.
4. Discovered ~1,000 unrelated pre-existing staged changes spanning the
   whole `OneDrive - Capgemini` repo root; reset the index and re-staged
   only this project folder to keep the commit clean.
5. Committed the project scaffold as `e0f30cf` on `add-grill-skill`.
6. Push to `origin` failed - `Repository not found`. **Blocked pending
   user confirmation of the correct remote/credentials.**
7. Created this file plus `memory.md`, `lesson.md`, `scratchpad.md`,
   `masterprompt.md` at the user's request.

## Next decision points (need a human call, not a default)

- Streamlit vs. Tkinter/ttk for the UI going forward.
- Correct GitHub remote / credentials so the branch can actually be pushed.
- Real FLARE and SuccessFactors target schemas (currently unknown).
- Target Python version (spec says 3.11+, `pyproject.toml` pins >=3.12,
  prior session actually ran on 3.10 - not yet reconciled).
