"""Eligibility validation page: run the rules engine against synthetic
context data for a selected nomination and show per-rule + overall results."""
from __future__ import annotations

import streamlit as st

from domain.enums import CheckSource, RuleResultStatus
from repositories.sqlite_repository import SqliteRepository
from services.eligibility_engine import RuleDefinition, decide, evaluate_rules


def _hs_rule(ctx: dict) -> RuleResultStatus:
    if "hs_completed" not in ctx:
        return RuleResultStatus.DATA_UNAVAILABLE
    return RuleResultStatus.PASS if ctx["hs_completed"] else RuleResultStatus.FAIL


def _doselect_rule(ctx: dict) -> RuleResultStatus:
    if "doselect_score" not in ctx:
        return RuleResultStatus.DATA_UNAVAILABLE
    return RuleResultStatus.PASS if ctx["doselect_score"] >= 60 else RuleResultStatus.FAIL


def _imocha_rule(ctx: dict) -> RuleResultStatus:
    if "imocha_score" not in ctx:
        return RuleResultStatus.DATA_UNAVAILABLE
    return RuleResultStatus.PASS if ctx["imocha_score"] >= 60 else RuleResultStatus.FAIL


DEFAULT_RULES = [
    RuleDefinition("HS Completion", CheckSource.HS_REPORT, _hs_rule),
    RuleDefinition("DoSelect Score >= 60", CheckSource.DOSELECT, _doselect_rule),
    RuleDefinition("iMocha Score >= 60", CheckSource.IMOCHA, _imocha_rule),
]


def render(repo: SqliteRepository) -> None:
    st.header("Eligibility validation")

    noms = repo.list_nominations()
    if not noms:
        st.info("No nominations to validate yet.")
        return

    nom_labels = {f"{n.id[:8]}... ({n.status.value})": n.id for n in noms}
    label = st.selectbox("Select nomination", list(nom_labels.keys()))
    nomination_id = nom_labels[label]

    st.caption("Context inputs simulate HS Report / DoSelect / iMocha source data. "
               "Leave a checkbox at its default 'unknown' state to simulate data not yet available.")
    col1, col2, col3 = st.columns(3)
    with col1:
        hs_known = st.checkbox("HS Report available", value=True)
        hs_completed = st.checkbox("HS completed", value=True) if hs_known else None
    with col2:
        ds_known = st.checkbox("DoSelect available", value=True)
        ds_score = st.number_input("DoSelect score", 0, 100, 75) if ds_known else None
    with col3:
        im_known = st.checkbox("iMocha available", value=True)
        im_score = st.number_input("iMocha score", 0, 100, 75) if im_known else None

    if st.button("Run eligibility check"):
        context = {}
        if hs_known:
            context["hs_completed"] = hs_completed
        if ds_known:
            context["doselect_score"] = ds_score
        if im_known:
            context["imocha_score"] = im_score

        rule_results = evaluate_rules(nomination_id, context, DEFAULT_RULES)
        rules_by_name = {r.name: r for r in DEFAULT_RULES}
        decision = decide(nomination_id, rule_results, rules_by_name)

        repo.add_eligibility_results(rule_results)
        repo.add_eligibility_decision(decision)

        badge = {"Eligible": "success", "NotEligible": "error", "PendingCriteria": "warning"}
        style = badge.get(decision.status.value, "info")
        getattr(st, style)(f"Overall decision: {decision.status.value}")
        for reason in decision.reasons:
            st.write(f"- {reason}")

    st.subheader("History for this nomination")
    rows = repo.list_eligibility_results(nomination_id)
    if rows:
        st.dataframe(
            [{"Rule": r["rule_name"], "Source": r["rule_source"], "Result": r["result"],
              "Detail": r["detail"], "Override": bool(r["is_manual_override"])} for r in rows],
            use_container_width=True,
        )
    else:
        st.caption("No eligibility checks run yet for this nomination.")
