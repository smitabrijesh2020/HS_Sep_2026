"""Eligibility rules engine.

Design principles (from requirements):
  * Each configured rule (HS completion, DoSelect, iMocha, required learning,
    experience, grade, role, ...) is evaluated and stored as its own result.
  * The overall decision is derived from the individual results with
    human-readable reasons.
  * Missing/unavailable source data must NEVER be treated as an automatic
    Fail / adverse decision. It routes the case to PendingCriteria /
    PendingManualReview instead.
  * Manual overrides are supported but require actor + reason + timestamp,
    and are recorded as their own rule result (is_manual_override=True) -
    they never silently overwrite the automated result.

This module has no I/O and no framework dependency, so it is fully unit
testable; the repository/service layer wires it to real data sources.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Sequence

from domain.enums import CheckSource, EligibilityStatus, RuleResultStatus
from domain.models import EligibilityDecision, EligibilityRuleResult


@dataclass(frozen=True)
class RuleDefinition:
    """A configurable, named eligibility rule.

    `evaluate` receives a dict of context data for the nomination (e.g.
    {"hs_completion": True, "imocha_score": 78, ...}) and must return a
    RuleResultStatus. It should return DATA_UNAVAILABLE (never FAIL) when the
    relevant source system has no record for this learner yet.
    """

    name: str
    source: CheckSource
    evaluate: Callable[[dict], RuleResultStatus]
    required: bool = True  # if False, a Fail here does not block eligibility


def evaluate_rules(
    nomination_id: str,
    context: dict,
    rules: Sequence[RuleDefinition],
) -> list[EligibilityRuleResult]:
    """Evaluate every configured rule against the supplied context data."""
    results: list[EligibilityRuleResult] = []
    for rule in rules:
        try:
            status = rule.evaluate(context)
        except Exception as exc:  # defensive: a broken rule must not crash eligibility
            status = RuleResultStatus.DATA_UNAVAILABLE
            detail = f"Rule '{rule.name}' raised an error during evaluation: {exc!r}"
        else:
            detail = _describe(rule, status, context)
        results.append(
            EligibilityRuleResult(
                nomination_id=nomination_id,
                rule_source=rule.source.value,
                rule_name=rule.name,
                result=status,
                detail=detail,
            )
        )
    return results


def _describe(rule: RuleDefinition, status: RuleResultStatus, context: dict) -> str:
    if status is RuleResultStatus.PASS:
        return f"{rule.name}: requirement met."
    if status is RuleResultStatus.FAIL:
        return f"{rule.name}: requirement not met."
    if status is RuleResultStatus.DATA_UNAVAILABLE:
        return f"{rule.name}: source data not yet available - routed for review, not treated as a failure."
    if status is RuleResultStatus.PENDING:
        return f"{rule.name}: evaluation pending."
    return f"{rule.name}: not applicable for this nomination."


def decide(
    nomination_id: str,
    rule_results: Sequence[EligibilityRuleResult],
    rules_by_name: dict[str, RuleDefinition] | None = None,
) -> EligibilityDecision:
    """Roll individual rule results into one overall decision + reasons.

    Logic:
      - Any required rule with result FAIL -> NOT_ELIGIBLE (unless it has a
        valid, non-expired manual override attached elsewhere; overrides are
        applied by calling `apply_manual_override` before re-deciding).
      - No FAIL, but at least one required rule PENDING/DATA_UNAVAILABLE ->
        PENDING_CRITERIA (human review needed; not an adverse decision).
      - All required rules PASS (or NOT_APPLICABLE) -> ELIGIBLE.
    """
    rules_by_name = rules_by_name or {}
    reasons: list[str] = []
    has_fail = False
    has_pending = False

    for r in rule_results:
        rule_def = rules_by_name.get(r.rule_name)
        required = rule_def.required if rule_def else True

        if r.is_manual_override:
            reasons.append(
                f"Manual override on '{r.rule_name}' by {r.override_actor} "
                f"at {r.override_at}: {r.override_reason}"
            )
            continue

        if r.result is RuleResultStatus.FAIL and required:
            has_fail = True
            reasons.append(r.detail)
        elif r.result in (RuleResultStatus.PENDING, RuleResultStatus.DATA_UNAVAILABLE) and required:
            has_pending = True
            reasons.append(r.detail)
        elif r.result is RuleResultStatus.PASS:
            reasons.append(r.detail)
        # NOT_APPLICABLE / non-required FAIL are omitted from the adverse path

    # A manual override marked PASS on a previously failing rule can clear a fail;
    # callers should re-run evaluate_rules + decide after recording the override so
    # the override's PASS result naturally supersedes the prior FAIL entry.
    if has_fail:
        status = EligibilityStatus.NOT_ELIGIBLE
    elif has_pending:
        status = EligibilityStatus.PENDING_CRITERIA
    else:
        status = EligibilityStatus.ELIGIBLE

    return EligibilityDecision(
        nomination_id=nomination_id,
        status=status,
        reasons=tuple(reasons),
        rule_result_ids=tuple(r.id for r in rule_results),
    )


def apply_manual_override(
    nomination_id: str,
    rule_name: str,
    rule_source: CheckSource,
    new_result: RuleResultStatus,
    actor: str,
    reason: str,
) -> EligibilityRuleResult:
    """Record an authorized manual override. Mandatory: actor + reason.

    This never mutates history in place - it appends a new rule result row
    so the automated result and the override remain independently auditable.
    """
    if not actor or not reason:
        raise ValueError("Manual overrides require both an actor and a reason.")
    return EligibilityRuleResult(
        nomination_id=nomination_id,
        rule_source=rule_source.value,
        rule_name=rule_name,
        result=new_result,
        detail=f"Manual override applied: {reason}",
        is_manual_override=True,
        override_reason=reason,
        override_actor=actor,
        override_at=datetime.utcnow(),
    )
