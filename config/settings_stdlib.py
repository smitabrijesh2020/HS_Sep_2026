"""Dependency-free settings loader used by the runnable MVP slice in this
session (stdlib `os.environ` + simple .env parsing only - no pydantic).

Mirrors the field set in `config/settings.py`. Once pydantic is installed
in a real environment, prefer `settings.get_settings()` instead; this
module exists solely so the slice can run inside a sandbox with no package
installation available.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _load_dotenv(path: str = ".env") -> dict[str, str]:
    values: dict[str, str] = {}
    p = Path(path)
    if not p.exists():
        return values
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        values[key.strip()] = val.split("#", 1)[0].strip()
    return values


@dataclass
class SimpleSettings:
    database_path: str = "hs_nomination.db"
    graph_dry_run: bool = True
    org_timezone: str = "Asia/Kolkata"
    escalation_offsets: dict = field(
        default_factory=lambda: {
            "Launch": 0,
            "Reminder1": 3,
            "Reminder2": 5,
            "Escalation": 7,
            "FinalReminder": 9,
            "ClosureReview": 11,
        }
    )


def get_simple_settings(env_file: str = ".env") -> SimpleSettings:
    values = {**_load_dotenv(env_file), **os.environ}
    db_url = values.get("DATABASE_URL", "sqlite:///./hs_nomination.db")
    db_path = db_url.replace("sqlite:///", "") if db_url.startswith("sqlite:///") else "hs_nomination.db"
    return SimpleSettings(
        database_path=db_path,
        graph_dry_run=values.get("GRAPH_DRY_RUN", "true").lower() != "false",
        org_timezone=values.get("ORG_TIMEZONE", "Asia/Kolkata"),
    )
