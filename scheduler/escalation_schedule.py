"""Escalation date calculator for the communication scheduler.

Default schedule (configurable via config.settings):
  Day 0  Launch
  Day 3  Reminder 1
  Day 5  Reminder 2
  Day 7  Escalation
  Day 9  Final reminder
  Day 11 Mark for manual review / closure

Dates are calculated from the applicable launch/nomination-window date, in
the organization's configured timezone, with an option to count business
days only. Suppressed/withdrawn/completed nominations must be excluded by
the caller before scheduling (this module only computes dates).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from domain.enums import CommunicationType

DEFAULT_OFFSETS: dict[CommunicationType, int] = {
    CommunicationType.LAUNCH: 0,
    CommunicationType.REMINDER_1: 3,
    CommunicationType.REMINDER_2: 5,
    CommunicationType.ESCALATION: 7,
    CommunicationType.FINAL_REMINDER: 9,
    CommunicationType.CLOSURE_REVIEW: 11,
}


@dataclass(frozen=True)
class ScheduleConfig:
    offsets: dict[CommunicationType, int] = None  # type: ignore[assignment]
    business_days_only: bool = False

    def __post_init__(self):
        if self.offsets is None:
            object.__setattr__(self, "offsets", dict(DEFAULT_OFFSETS))


def _add_days(start: date, days: int, business_days_only: bool) -> date:
    if not business_days_only:
        return start + timedelta(days=days)
    current = start
    remaining = days
    step = 1 if days >= 0 else -1
    while remaining != 0:
        current += timedelta(days=step)
        if current.weekday() < 5:  # Mon-Fri
            remaining -= step
    return current


def compute_due_date(
    launch_date: date | datetime,
    comm_type: CommunicationType,
    config: ScheduleConfig | None = None,
) -> date:
    config = config or ScheduleConfig()
    if isinstance(launch_date, datetime):
        launch_date = launch_date.date()
    offset = config.offsets.get(comm_type)
    if offset is None:
        raise ValueError(f"No configured offset for communication type {comm_type}")
    return _add_days(launch_date, offset, config.business_days_only)


def compute_full_schedule(
    launch_date: date | datetime, config: ScheduleConfig | None = None
) -> dict[CommunicationType, date]:
    config = config or ScheduleConfig()
    return {ct: compute_due_date(launch_date, ct, config) for ct in config.offsets}


def is_due(
    comm_type: CommunicationType,
    launch_date: date | datetime,
    as_of: date,
    config: ScheduleConfig | None = None,
) -> bool:
    """True once `as_of` has reached (or passed) the due date for this step."""
    return as_of >= compute_due_date(launch_date, comm_type, config)
