"""Unit tests for services.status_mapping_service."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from domain.enums import RuleResultStatus
from domain.mapping_models import CanonicalField
from services.status_mapping_service import (
    StatusMappingConfig,
    StatusValueRule,
    classify_status_value,
    load_status_mapping_config,
    save_status_mapping_config,
)


class TestClassifyStatusValueTextMode(unittest.TestCase):
    def setUp(self):
        self.rule = StatusValueRule(
            canonical_field=CanonicalField.HS_COMPLETION_STATUS,
            mode="text_values",
            pass_values=("completed", "cleared"),
            fail_values=("not started", "failed"),
            pending_values=("in progress",),
        )

    def test_known_pass_value(self):
        status, _ = classify_status_value("Completed", self.rule)
        self.assertEqual(status, RuleResultStatus.PASS)

    def test_known_fail_value(self):
        status, _ = classify_status_value("Failed", self.rule)
        self.assertEqual(status, RuleResultStatus.FAIL)

    def test_known_pending_value_is_data_unavailable(self):
        status, _ = classify_status_value("In Progress", self.rule)
        self.assertEqual(status, RuleResultStatus.DATA_UNAVAILABLE)

    def test_unrecognized_value_is_data_unavailable_never_guessed(self):
        status, _ = classify_status_value("Some new status nobody configured", self.rule)
        self.assertEqual(status, RuleResultStatus.DATA_UNAVAILABLE)

    def test_case_and_whitespace_variance_still_classifies(self):
        status, _ = classify_status_value("  COMPLETED  ", self.rule)
        self.assertEqual(status, RuleResultStatus.PASS)

    def test_blank_value_is_data_unavailable(self):
        status, _ = classify_status_value(None, self.rule)
        self.assertEqual(status, RuleResultStatus.DATA_UNAVAILABLE)

    def test_no_rule_configured_is_data_unavailable(self):
        status, _ = classify_status_value("Completed", None)
        self.assertEqual(status, RuleResultStatus.DATA_UNAVAILABLE)


class TestClassifyStatusValueNumericMode(unittest.TestCase):
    def setUp(self):
        self.rule = StatusValueRule(
            canonical_field=CanonicalField.IMOCHA_STATUS, mode="numeric_threshold",
            numeric_pass_threshold=60.0,
        )

    def test_above_threshold_passes(self):
        status, _ = classify_status_value(75, self.rule)
        self.assertEqual(status, RuleResultStatus.PASS)

    def test_below_threshold_fails(self):
        status, _ = classify_status_value(40, self.rule)
        self.assertEqual(status, RuleResultStatus.FAIL)

    def test_exactly_at_threshold_passes(self):
        status, _ = classify_status_value(60, self.rule)
        self.assertEqual(status, RuleResultStatus.PASS)

    def test_non_numeric_value_is_data_unavailable(self):
        status, _ = classify_status_value("not a number", self.rule)
        self.assertEqual(status, RuleResultStatus.DATA_UNAVAILABLE)

    def test_no_threshold_configured_is_data_unavailable(self):
        rule = StatusValueRule(canonical_field=CanonicalField.IMOCHA_STATUS, mode="numeric_threshold")
        status, _ = classify_status_value(75, rule)
        self.assertEqual(status, RuleResultStatus.DATA_UNAVAILABLE)


class TestStatusMappingConfigRoundTrip(unittest.TestCase):
    def test_save_then_load_reproduces_config(self):
        config = StatusMappingConfig(
            rules={
                CanonicalField.IMOCHA_STATUS.value: StatusValueRule(
                    canonical_field=CanonicalField.IMOCHA_STATUS, mode="numeric_threshold",
                    numeric_pass_threshold=60.0,
                )
            }
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "status_mappings.json"
            save_status_mapping_config(config, path)
            reloaded = load_status_mapping_config(path)
        rule = reloaded.rules[CanonicalField.IMOCHA_STATUS.value]
        self.assertEqual(rule.numeric_pass_threshold, 60.0)

    def test_missing_file_returns_empty_config(self):
        config = load_status_mapping_config(Path("Z:/does/not/exist/status_mappings.json"))
        self.assertEqual(config.rules, {})


if __name__ == "__main__":
    unittest.main()
