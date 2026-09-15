"""Configurable status-value classification (Pass / Fail / DataUnavailable).

Replaces the hardcoded `>= 60` threshold and implicit "Completed" string
check previously baked into `app/ui/eligibility_page.py`. An unrecognized
or unconfigured value always routes to DataUnavailable - it is never
guessed as Pass or Fail, per masterprompt.md's "do not invent business
values" rule.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from domain.enums import RuleResultStatus
from domain.mapping_models import CanonicalField
from utils.normalizers import is_blank, normalize_status_text, normalize_whitespace


@dataclass(frozen=True)
class StatusValueRule:
    canonical_field: CanonicalField
    mode: str  # "text_values" | "numeric_threshold"
    pass_values: tuple[str, ...] = ()   # pre-normalized (lower/trimmed) literals
    fail_values: tuple[str, ...] = ()
    pending_values: tuple[str, ...] = ()
    numeric_pass_threshold: float | None = None


@dataclass
class StatusMappingConfig:
    version: int = 1
    rules: dict[str, StatusValueRule] = field(default_factory=dict)  # keyed by CanonicalField.value


def _rule_to_dict(rule: StatusValueRule) -> dict:
    return {
        "canonical_field": rule.canonical_field.value,
        "mode": rule.mode,
        "pass_values": list(rule.pass_values),
        "fail_values": list(rule.fail_values),
        "pending_values": list(rule.pending_values),
        "numeric_pass_threshold": rule.numeric_pass_threshold,
    }


def _rule_from_dict(data: dict) -> StatusValueRule:
    return StatusValueRule(
        canonical_field=CanonicalField(data["canonical_field"]),
        mode=data["mode"],
        pass_values=tuple(data.get("pass_values", [])),
        fail_values=tuple(data.get("fail_values", [])),
        pending_values=tuple(data.get("pending_values", [])),
        numeric_pass_threshold=data.get("numeric_pass_threshold"),
    )


def load_status_mapping_config(path: Path) -> StatusMappingConfig:
    if not path.exists():
        return StatusMappingConfig()
    raw = json.loads(path.read_text(encoding="utf-8"))
    return StatusMappingConfig(
        version=raw.get("version", 1),
        rules={k: _rule_from_dict(v) for k, v in raw.get("rules", {}).items()},
    )


def save_status_mapping_config(config: StatusMappingConfig, path: Path) -> None:
    payload = {"version": config.version, "rules": {k: _rule_to_dict(v) for k, v in config.rules.items()}}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def classify_status_value(
    raw_value: object, rule: StatusValueRule | None
) -> tuple[RuleResultStatus, str]:
    """Returns (status, normalized_value_for_provenance).

    No rule configured, or a blank cell -> DataUnavailable (a config/data
    gap, never treated as adverse). An unrecognized text value or a
    non-numeric value in numeric mode is also DataUnavailable, never FAIL.
    """
    if rule is None or is_blank(raw_value):
        return RuleResultStatus.DATA_UNAVAILABLE, normalize_whitespace(raw_value)

    if rule.mode == "numeric_threshold":
        try:
            numeric = float(raw_value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return RuleResultStatus.DATA_UNAVAILABLE, normalize_whitespace(raw_value)
        normalized = str(numeric)
        if rule.numeric_pass_threshold is None:
            return RuleResultStatus.DATA_UNAVAILABLE, normalized
        status = (
            RuleResultStatus.PASS if numeric >= rule.numeric_pass_threshold else RuleResultStatus.FAIL
        )
        return status, normalized

    # text_values mode
    normalized = normalize_status_text(raw_value)
    if normalized in rule.pass_values:
        return RuleResultStatus.PASS, normalized
    if normalized in rule.fail_values:
        return RuleResultStatus.FAIL, normalized
    # Includes both explicit pending_values and any spelling not yet seen/configured.
    return RuleResultStatus.DATA_UNAVAILABLE, normalized
