"""Nominations page: create a nomination with duplicate-active-nomination
prevention (services.nomination_service.create_nomination)."""
from __future__ import annotations

import streamlit as st

from repositories.sqlite_repository import SqliteRepository
from services.nomination_service import DuplicateActiveNominationError, create_nomination


def render(repo: SqliteRepository) -> None:
    st.header("Nominations")

    employees = repo.list_employees()
    programs = repo.list_programs()
    batches = repo.list_batches()

    if not employees or not programs or not batches:
        st.warning("Seed synthetic employees, and create at least one program + batch, before nominating.")
        return

    emp_lookup = {f"{e['display_name']} ({e['employee_code']})": e["id"] for e in employees}
    program_lookup = {p["name"]: p["id"] for p in programs}

    with st.expander("Add nomination"):
        with st.form("add_nomination"):
            emp_key = st.selectbox("Employee*", list(emp_lookup.keys()))
            program_name = st.selectbox("Program*", list(program_lookup.keys()))
            program_id = program_lookup[program_name]
            batches_for_program = [b for b in batches if b["program_id"] == program_id]
            if not batches_for_program:
                st.info("No batches under this program yet.")
                batch_key = None
            else:
                batch_options = {b["trf_number"]: b["id"] for b in batches_for_program}
                batch_key = st.selectbox("Batch (TRF)*", list(batch_options.keys()))
            submitted = st.form_submit_button("Submit nomination")

            if submitted:
                if not batch_key:
                    st.error("Select a batch.")
                else:
                    employee_id = emp_lookup[emp_key]
                    batch_id = batch_options[batch_key]
                    existing = repo.list_nominations(employee_id=employee_id)
                    try:
                        nomination, audit = create_nomination(
                            existing, employee_id, program_id, batch_id, actor="ui-user",
                        )
                    except DuplicateActiveNominationError as exc:
                        st.error(f"Not created - duplicate active nomination detected: {exc}")
                    else:
                        repo.add_nomination(nomination)
                        repo.add_audit(audit)
                        st.success("Nomination submitted.")
                        st.rerun()

    st.subheader("All nominations")
    all_noms = repo.list_nominations()
    if not all_noms:
        st.info("No nominations yet.")
        return

    emp_by_id = {e["id"]: e for e in employees}
    prog_by_id = {p["id"]: p["name"] for p in programs}
    batch_by_id = {b["id"]: b["trf_number"] for b in batches}

    table = []
    for n in all_noms:
        emp = emp_by_id.get(n.employee_id)
        table.append({
            "Employee": emp["display_name"] if emp else "?",
            "Program": prog_by_id.get(n.program_id, "?"),
            "Batch": batch_by_id.get(n.batch_id, "?"),
            "Status": n.status.value,
            "Source": n.source,
            "Created": n.created_at.isoformat(timespec="minutes"),
        })
    st.dataframe(table, use_container_width=True)
