"""Batches page: create batches under a program, show seat utilization."""
from __future__ import annotations

import streamlit as st

from domain.enums import BatchStatus
from domain.models import AuditLogEntry, Batch
from repositories.sqlite_repository import SqliteRepository


def render(repo: SqliteRepository) -> None:
    st.header("Batches")

    programs = repo.list_programs()
    if not programs:
        st.warning("Create a program first on the Programs page.")
        return

    program_lookup = {p["name"]: p["id"] for p in programs}

    with st.expander("Create new batch"):
        with st.form("create_batch"):
            program_name = st.selectbox("Program*", list(program_lookup.keys()))
            trf_number = st.text_input("TRF number*")
            capacity = st.number_input("Capacity", min_value=0, value=20)
            trainer = st.text_input("Trainer")
            location = st.text_input("Location")
            delivery_mode = st.selectbox("Delivery mode", ["Virtual", "In-Person", "Hybrid"])
            submitted = st.form_submit_button("Create batch")
            if submitted:
                if not trf_number.strip():
                    st.error("TRF number is required.")
                else:
                    batch = Batch(
                        program_id=program_lookup[program_name], trf_number=trf_number.strip(),
                        capacity=int(capacity), trainer=trainer, location=location,
                        delivery_mode=delivery_mode, status=BatchStatus.PLANNED,
                        created_by="ui-user", updated_by="ui-user",
                    )
                    repo.add_batch(batch)
                    repo.add_audit(AuditLogEntry(
                        entity_type="Batch", entity_id=batch.id, action="Created",
                        actor="ui-user", detail=f"Batch '{batch.trf_number}' created under {program_name}.",
                    ))
                    st.success(f"Batch '{batch.trf_number}' created.")
                    st.rerun()

    rows = repo.list_batches()
    if not rows:
        st.info("No batches yet.")
        return

    program_name_by_id = {p["id"]: p["name"] for p in programs}
    table = []
    for r in rows:
        summary = repo.seat_summary(r["id"])
        table.append({
            "Program": program_name_by_id.get(r["program_id"], "?"),
            "TRF": r["trf_number"], "Status": r["status"], "Capacity": summary["capacity"],
            "Filled": summary["filled"], "Available": summary["available"],
            "Waitlisted": summary["waitlisted"], "Utilization %": round(summary["utilization"] * 100, 1),
        })
    st.dataframe(table, use_container_width=True)
