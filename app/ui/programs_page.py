"""Programs page: create + list programs. See app/main.py verification note."""
from __future__ import annotations

import streamlit as st

from domain.enums import ProgramStatus
from domain.models import AuditLogEntry, Program
from repositories.sqlite_repository import SqliteRepository


def render(repo: SqliteRepository) -> None:
    st.header("Programs")

    with st.expander("Create new program"):
        with st.form("create_program"):
            name = st.text_input("Program name*")
            owner = st.text_input("Owner")
            business_unit = st.text_input("Business unit")
            technology = st.text_input("Technology")
            description = st.text_area("Description")
            submitted = st.form_submit_button("Create program")
            if submitted:
                if not name.strip():
                    st.error("Program name is required.")
                else:
                    program = Program(
                        name=name.strip(), owner=owner, business_unit=business_unit,
                        technology=technology, description=description,
                        status=ProgramStatus.DRAFT, created_by="ui-user", updated_by="ui-user",
                    )
                    repo.add_program(program)
                    repo.add_audit(AuditLogEntry(
                        entity_type="Program", entity_id=program.id, action="Created",
                        actor="ui-user", detail=f"Program '{program.name}' created via UI.",
                    ))
                    st.success(f"Program '{program.name}' created.")
                    st.rerun()

    rows = repo.list_programs()
    if not rows:
        st.info("No programs yet. Use 'Create new program' above to add one.")
        return

    st.dataframe(
        [{"Name": r["name"], "Status": r["status"], "Owner": r["owner"], "BU": r["business_unit"],
          "Technology": r["technology"], "ID": r["id"]} for r in rows],
        use_container_width=True,
    )
