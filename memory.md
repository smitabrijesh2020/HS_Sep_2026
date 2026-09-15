# Project Memory

Durable, cross-session facts about this project. Read this before doing
anything else in this repo. Last updated: 2026-09-15.

## What this project is

"HS Nomination Automation Manager" - automation for the internal Capgemini
HS NB Program nomination lifecycle (nomination collection, prerequisite
matching against HS/Do-select/iMocha reports, eligibility decisions,
reminders, final FLARE/SuccessFactors handoff). Full target scope is in
[masterprompt.md](masterprompt.md). Current actual scope is much smaller -
see [progress.md](progress.md).

## Location and identity

- Project folder: `C:\Users\smitkuma\OneDrive - Capgemini\Documents\HS Automation\hs-nomination-automation`
- Parent folder `HS Automation` (one level up) also contains **real business
  data**: nomination/certification tracker workbooks and Outlook `.msg`
  exports. These are live, GDPR/employee-data-relevant files. Never copy
  their contents into code, tests, seed data, or committed docs - see
  `docs/security_privacy_checklist.md` for the specific filenames and what
  was and wasn't done with them.
- Git branch: `add-grill-skill`. Remote `origin` = `https://github.com/brijeshsmita/CapG_Sep_2019`.
- **Open blocker (2026-09-15):** `git push` to that remote failed with
  `remote: Repository not found`. Not yet resolved - confirm the correct
  repo/owner and that the environment's Git credentials have access before
  assuming any push will succeed.
- `gh` CLI is **not installed** in this environment. PR creation needs
  either installing it or using GitHub's web compare UI manually.

## Critical git topology gotcha

The git repository root is **not** this project folder, and not even the
`Documents` folder - it is the entire `OneDrive - Capgemini` root. The repo
therefore also tracks large amounts of unrelated personal content (Python
practice exercises, an Eclipse workspace, a stale nested `humbleRepo`) with
its own pre-existing uncommitted/staged changes that have nothing to do with
this project. **Never run `git add -A`, `git add .` from outside this
folder, or a bare `git commit` without first checking exactly what's
staged** - `git status`/`git commit` operate repo-wide regardless of your
current directory. Always scope `git add` to this project folder specifically
and verify the staged file list before committing. Full story in
[lesson.md](lesson.md).

## Architecture reality check

- `masterprompt.md` mandates a **Tkinter/ttk Windows desktop app**.
- What actually exists today is a **Streamlit** app (`app/main.py`,
  `app/ui/*.py`, run via `streamlit run app/main.py`). This is an
  unresolved conflict, not a mistake to silently paper over - a decision is
  needed on whether to continue in Streamlit or rebuild the UI layer in
  Tkinter/ttk per the original brief. See `docs/assumptions_and_decision_log.md`
  entry - the prior session scoped itself to a single vertical slice and did
  not attempt the full Tkinter UI.
- Persistence is SQLite via a hand-written `sqlite_repository.py` (tested,
  runnable) plus a target SQLAlchemy/Alembic schema (`orm_models.py`,
  `migrations/`) that is **unverified** - never executed against a real
  database in any session so far (sandbox had no package-index access).
- Microsoft Graph integration (`integrations/graph_client.py`) is
  **dry-run only**. No MSAL wiring against a real tenant exists yet.

## Data handling rules (do not relax these)

- `sample_data/seed_synthetic.py` must only ever generate fabricated
  names/emails/IDs. Never point it, or any test, at the real trackers in
  the parent `HS Automation` folder.
- No hard-coded credentials, tokens, or connection strings - verified clean
  as of 2026-09-15 (see lesson.md for how this was checked before pushing).
- `.env.example` = placeholders only. Real `.env` must never be committed
  (already covered by `.gitignore`).

## Key docs in this repo (read these, don't duplicate them)

- `docs/architecture_overview.md` - design/architecture detail
- `docs/assumptions_and_decision_log.md` - numbered decisions with rationale
- `docs/traceability_matrix.md` - requirement-by-requirement test status
- `docs/security_privacy_checklist.md` - real-data findings and controls
- `docs/operations_runbook.md` - how to operate what exists today
- [progress.md](progress.md) - gap analysis vs. masterprompt.md
- [lesson.md](lesson.md) - operational gotchas learned the hard way
- [scratchpad.md](scratchpad.md) - informal open TODOs, not authoritative
