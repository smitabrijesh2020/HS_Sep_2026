"""Application settings via pydantic-settings.

NOTE ON VERIFICATION STATUS: `pydantic`/`pydantic-settings` could not be
installed in this sandbox (no outbound package-index access), so this
module has not been executed here. It follows standard pydantic-settings
v2 conventions - install the pinned dependencies from pyproject.toml and
run `pytest` to verify before relying on it. The runnable MVP slice for
this session reads configuration via `config/settings_stdlib.py` instead.
"""
from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = Field(default="development", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    database_url: str = Field(default="sqlite:///./hs_nomination.db", alias="DATABASE_URL")
    org_timezone: str = Field(default="Asia/Kolkata", alias="ORG_TIMEZONE")

    graph_tenant_id: str = Field(default="", alias="GRAPH_TENANT_ID")
    graph_client_id: str = Field(default="", alias="GRAPH_CLIENT_ID")
    graph_client_certificate_path: str = Field(default="", alias="GRAPH_CLIENT_CERTIFICATE_PATH")
    graph_sender_upn: str = Field(default="", alias="GRAPH_SENDER_UPN")
    graph_dry_run: bool = Field(default=True, alias="GRAPH_DRY_RUN")

    escalation_day0_launch: int = Field(default=0, alias="ESCALATION_DAY0_LAUNCH")
    escalation_day_reminder_1: int = Field(default=3, alias="ESCALATION_DAY_REMINDER_1")
    escalation_day_reminder_2: int = Field(default=5, alias="ESCALATION_DAY_REMINDER_2")
    escalation_day_escalation: int = Field(default=7, alias="ESCALATION_DAY_ESCALATION")
    escalation_day_final_reminder: int = Field(default=9, alias="ESCALATION_DAY_FINAL_REMINDER")
    escalation_day_close_review: int = Field(default=11, alias="ESCALATION_DAY_CLOSE_REVIEW")

    audit_log_retention_days: int = Field(default=365, alias="AUDIT_LOG_RETENTION_DAYS")
    communication_log_retention_days: int = Field(default=365, alias="COMMUNICATION_LOG_RETENTION_DAYS")


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
