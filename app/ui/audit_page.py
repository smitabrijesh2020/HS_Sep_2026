"""Audit history page - read-only trail of who changed what and when."""
from __future__ import annotations

import streamlit as st

from repositories.sqlite_repository import SqliteRepository


def render(repo: SqliteRepository) -> None:
    st.header("Audit history")

    rows = repo.list_audit()
    if not rows:
        st.info("No audit events recorded yet.")
        return

    st.dataframe(
        [{"When": r["occurred_at"], "Entity": r["entity_type"], "Entity ID": r["entity_id"][:8] + "...",
          "Action": r["action"], "Actor": r["actor"], "Detail": r["detail"]} for r in rows],
        use_container_width=True,
    )
