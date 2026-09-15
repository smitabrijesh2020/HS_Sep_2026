"""Communications page: dry-run dispatch with idempotency, view log.

Real sending is intentionally not wired here - see
integrations/graph_client.py and project rule "do not send real email
during development or testing."
"""
from __future__ import annotations

from datetime import date

import streamlit as st

from domain.enums import CommunicationType
from domain.models import AuditLogEntry
from repositories.sqlite_repository import SqliteRepository
from services.communication_service import SendResult, dispatch


def render(repo: SqliteRepository) -> None:
    st.header("Communications (dry-run only)")
    st.caption("GRAPH_DRY_RUN is enforced true for this session. No real email is sent.")

    noms = repo.list_nominations()
    if not noms:
        st.info("No nominations to communicate with yet.")
        return

    nom_labels = {f"{n.id[:8]}... ({n.status.value})": n for n in noms}
    label = st.selectbox("Select nomination", list(nom_labels.keys()))
    nomination = nom_labels[label]

    comm_type = st.selectbox("Communication type", [c.value for c in CommunicationType])
    template_version = st.text_input("Template version", value="v1")
    schedule_date = st.date_input("Schedule date", value=date.today()).isoformat()

    if st.button("Dispatch (dry-run)"):
        existing_log = repo.list_communication_log(nomination.id)
        entry = dispatch(
            employee_id=nomination.employee_id,
            nomination_id=nomination.id,
            comm_type=CommunicationType(comm_type),
            template_version=template_version,
            schedule_date=schedule_date,
            existing_log=existing_log,
            send_fn=lambda: SendResult(success=True, provider_message_id="unused-in-dry-run"),
            dry_run=True,
        )
        repo.add_communication_log(entry)
        repo.add_audit(AuditLogEntry(
            entity_type="Communication", entity_id=entry.id, action=entry.status.value,
            actor="ui-user", detail=f"{comm_type} dry-run for nomination {nomination.id}.",
        ))
        if entry.status.value == "Suppressed":
            st.warning("Suppressed: an identical communication already succeeded (idempotency check).")
        else:
            st.success(f"Dry-run recorded with status: {entry.status.value}")

    st.subheader("Communication log for this nomination")
    log = repo.list_communication_log(nomination.id)
    if log:
        st.dataframe(
            [{"Type": e.comm_type.value, "Status": e.status.value, "Template": e.template_version,
              "Retries": e.retry_count, "Idempotency key": e.idempotency_key[:12] + "...",
              "Sent at": e.sent_at.isoformat(timespec="minutes") if e.sent_at else ""} for e in log],
            use_container_width=True,
        )
    else:
        st.caption("No communications recorded yet.")
