import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from domain.enums import CheckSource, EligibilityStatus, RuleResultStatus
from services.eligibility_engine import RuleDefinition, apply_manual_override, decide, evaluate_rules


def hs_rule(ctx):
    if "hs_completed" not in ctx:
        return RuleResultStatus.DATA_UNAVAILABLE
    return RuleResultStatus.PASS if ctx["hs_completed"] else RuleResultStatus.FAIL


def score_rule(threshold, key):
    def _rule(ctx):
        if key not in ctx:
            return RuleResultStatus.DATA_UNAVAILABLE
        return RuleResultStatus.PASS if ctx[key] >= threshold else RuleResultStatus.FAIL
    return _rule


RULES = [
    RuleDefinition("HS Completion", CheckSource.HS_REPORT, hs_rule),
    RuleDefinition("DoSelect >= 60", CheckSource.DOSELECT, score_rule(60, "doselect_score")),
    RuleDefinition("iMocha >= 60", CheckSource.IMOCHA, score_rule(60, "imocha_score")),
]
RULES_BY_NAME = {r.name: r for r in RULES}


class TestEligibilityEngine(unittest.TestCase):
    def test_all_pass_is_eligible(self):
        ctx = {"hs_completed": True, "doselect_score": 80, "imocha_score": 90}
        results = evaluate_rules("nom1", ctx, RULES)
        decision = decide("nom1", results, RULES_BY_NAME)
        self.assertEqual(decision.status, EligibilityStatus.ELIGIBLE)
        self.assertEqual(len(decision.reasons), 3)

    def test_any_fail_is_not_eligible(self):
        ctx = {"hs_completed": False, "doselect_score": 80, "imocha_score": 90}
        results = evaluate_rules("nom1", ctx, RULES)
        decision = decide("nom1", results, RULES_BY_NAME)
        self.assertEqual(decision.status, EligibilityStatus.NOT_ELIGIBLE)

    def test_missing_data_is_pending_not_adverse(self):
        """Core requirement: incomplete/missing source data must never
        produce a final adverse (NotEligible) decision on its own."""
        ctx = {"hs_completed": True, "doselect_score": 80}  # imocha_score missing
        results = evaluate_rules("nom1", ctx, RULES)
        decision = decide("nom1", results, RULES_BY_NAME)
        self.assertEqual(decision.status, EligibilityStatus.PENDING_CRITERIA)
        self.assertNotEqual(decision.status, EligibilityStatus.NOT_ELIGIBLE)

    def test_broken_rule_does_not_crash_and_is_treated_as_unavailable(self):
        def broken_rule(ctx):
            raise RuntimeError("source system unreachable")

        rules = [RuleDefinition("Broken", CheckSource.OTHER, broken_rule)]
        results = evaluate_rules("nom1", {}, rules)
        self.assertEqual(results[0].result, RuleResultStatus.DATA_UNAVAILABLE)
        decision = decide("nom1", results, {r.name: r for r in rules})
        self.assertEqual(decision.status, EligibilityStatus.PENDING_CRITERIA)

    def test_manual_override_requires_actor_and_reason(self):
        with self.assertRaises(ValueError):
            apply_manual_override("nom1", "HS Completion", CheckSource.HS_REPORT,
                                    RuleResultStatus.PASS, actor="", reason="")

    def test_manual_override_recorded_and_included_in_reasons(self):
        override = apply_manual_override(
            "nom1", "HS Completion", CheckSource.HS_REPORT, RuleResultStatus.PASS,
            actor="validator@example.org", reason="Certificate verified out of band.",
        )
        self.assertTrue(override.is_manual_override)
        decision = decide("nom1", [override], RULES_BY_NAME)
        self.assertTrue(any("Manual override" in r for r in decision.reasons))

    def test_non_required_rule_failure_does_not_block_eligibility(self):
        optional_rule = RuleDefinition("Nice to have", CheckSource.OTHER, lambda c: RuleResultStatus.FAIL,
                                        required=False)
        results = evaluate_rules("nom1", {}, [optional_rule])
        decision = decide("nom1", results, {"Nice to have": optional_rule})
        self.assertNotEqual(decision.status, EligibilityStatus.NOT_ELIGIBLE)


if __name__ == "__main__":
    unittest.main()
