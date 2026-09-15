"""Streamlit entrypoint for the HS Nomination Automation MVP slice.

NOTE ON VERIFICATION STATUS: `streamlit` could not be installed in this
Cowork sandbox (no outbound package-index access), so this UI has been
written to standard Streamlit 1.38 API but NOT executed/screenshotted in
this session. Classify as "implemented but not externally verified" -
run `streamlit run app/main.py` after `pip install -e .` in an environment
with network access, then verify each page renders and the empty/error
states look correct before demoing.

Covers, for this vertical slice only: Programs, Batches, Nominations,
Eligibility, Communications (dry-run log), Audit history. The full page
set from the requirements (Executive overview, Exports, Administration,
Login/identity) is designed but deferred to a later increment - see
docs/traceability_matrix.md.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from app.ui import audit_page, batches_page, communications_page, eligibility_page, nominations_page, programs_page
from repositories.sqlite_repository import SqliteRepository

st.set_page_config(page_title="HS Nomination Automation", layout="wide")


@st.cache_resource
def get_repo() -> SqliteRepository:
    return SqliteRepository("hs_nomination.db")


def main() -> None:
    repo = get_repo()

    st.sidebar.title("HS Nomination Automation")
    st.sidebar.caption("MVP slice - synthetic data only. Not connected to production systems.")
    page = st.sidebar.radio(
        "Navigate",
        ["Programs", "Batches", "Nominations", "Eligibility", "Communications (dry-run)", "Audit history"],
    )

    if page == "Programs":
        programs_page.render(repo)
    elif page == "Batches":
        batches_page.render(repo)
    elif page == "Nominations":
        nominations_page.render(repo)
    elif page == "Eligibility":
        eligibility_page.render(repo)
    elif page == "Communications (dry-run)":
        communications_page.render(repo)
    elif page == "Audit history":
        audit_page.render(repo)


if __name__ == "__main__":
    main()
