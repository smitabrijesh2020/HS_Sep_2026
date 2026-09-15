# Architecture Overview

## Current state (as found)
The "HS Automation" folder contained no existing application code. It held
business planning artifacts only: a self-authored Dataverse-oriented data
architecture doc, a BAU process map (use cases), several BAU trackers
(nomination lists, certification/registration exports, an iMocha test
report), and Outlook `.msg` templates for the Welcome/Prerequisite mailers
and a couple of internal threads. There is no prior tech stack to preserve.

## Target architecture (this build)
Per explicit direction, the persistence target for this build is
**SQLite via SQLAlchemy**, not PostgreSQL, with Streamlit as the UI layer.
Layering:

```
Streamlit UI (app/ui/*.py)
  -> Service layer (services/*.py)  - business rules, framework-agnostic
  -> Repository layer (repositories/*.py) - persistence
  -> SQLite (MVP) — same ORM/migration pattern carries to Postgres later
  -> Microsoft Graph (integrations/graph_client.py) - dry-run only
  -> APScheduler (scheduler/*.py) - date math implemented; job runner not yet wired
  -> Power BI-ready views (reporting/*.sql, *.md) - designed only
  -> FLARE / SF exports (exports/*.py) - mapping template only, schema TBD
```

## Sandbox constraint that shaped this session's implementation
This Cowork sandbox has no outbound access to PyPI (pip install fails with a
proxy 403). SQLAlchemy, Alembic, Pydantic, and Streamlit could not be
installed, so those layers were written to spec but not executed here. To
still deliver a genuinely *verified* vertical slice, the business logic
(`domain/`, `services/`, `scheduler/escalation_schedule.py`) was kept
dependency-free (stdlib only) and paired with a stdlib-`sqlite3` repository
(`repositories/sqlite_repository.py`) that implements the same schema as
the SQLAlchemy models. 33 unit + integration tests run against this path
today; see docs/traceability_matrix.md for what's verified vs. designed.

## Why Dataverse-vs-Postgres/SQLite mattered
Your own `HS_Nomination_Automation_Data_Architecture.docx` (dated the same
day as this session) already specifies a 14-table Dataverse model. That
was flagged as a genuine fork rather than guessed at; you chose
Streamlit + SQLite for this build. The Dataverse doc's entity/field names
were used as a cross-reference when naming this schema so a later mapping
between the two is straightforward, but the two are not code-identical.
