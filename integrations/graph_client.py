"""Microsoft Graph email abstraction with mandatory dry-run mode.

Required organizational review before production use (see
docs/security_privacy_checklist.md and docs/operations_runbook.md):
  * Confirm delegated vs application permissions with the tenant admin.
  * Least-privileged Graph scope for sending mail is `Mail.Send` (application
    permission, admin-consented) - no broader mailbox scope should be
    requested.
  * Use certificate-based application authentication (MSAL confidential
    client with a client certificate), NOT a client secret and NEVER a
    mailbox password/basic auth.
  * This module never sends real email during development/testing. The
    default and only mode wired into this session's slice is dry-run;
    `GRAPH_DRY_RUN=false` requires an explicit, reviewed configuration
    change plus a real MSAL app registration.

Separation of concerns, per requirements: authentication, message
construction, the send operation, retries, and logging are each isolated
so any one of them can be swapped/mocked independently.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger("hs_automation.graph")


class GraphAuthError(Exception):
    pass


@dataclass(frozen=True)
class GraphConfig:
    tenant_id: str
    client_id: str
    client_certificate_path: str
    sender_upn: str
    dry_run: bool = True


class GraphAuthenticator:
    """Wraps MSAL confidential-client, certificate-based auth.

    NOT implemented against a live tenant in this session (would require a
    real app registration + certificate, and this task must not connect to
    production systems). `acquire_token` raises in non-dry-run mode until a
    real MSAL wiring is supplied - this is intentional, not an oversight.
    """

    def __init__(self, config: GraphConfig):
        self.config = config

    def acquire_token(self) -> str:
        if self.config.dry_run:
            return "dry-run-no-token"
        raise GraphAuthError(
            "Live Microsoft Graph authentication is not configured in this build. "
            "Wire a certificate-based MSAL ConfidentialClientApplication here only "
            "after tenant permissions (Mail.Send, application, admin-consented) "
            "have been granted and reviewed."
        )


def build_message(
    to_email: str,
    subject: str,
    html_body: str,
    template_version: str,
) -> dict:
    """Construct a Graph `sendMail` payload shape. Does not send it."""
    return {
        "message": {
            "subject": subject,
            "body": {"contentType": "HTML", "content": html_body},
            "toRecipients": [{"emailAddress": {"address": to_email}}],
            "internetMessageHeaders": [
                {"name": "X-HS-Automation-Template-Version", "value": template_version}
            ],
        },
        "saveToSentItems": "true",
    }


class GraphMailClient:
    """Send operation, isolated from auth and message construction.

    In dry-run mode (the only mode exercised in this session) it logs a
    sanitized summary (recipient domain only, not full address; subject
    only) and returns a synthetic message id - no network call is made.
    """

    def __init__(self, authenticator: GraphAuthenticator):
        self.authenticator = authenticator

    def send(self, message_payload: dict) -> str:
        cfg = self.authenticator.config
        token = self.authenticator.acquire_token()  # noqa: F841 - would be used by a real HTTP call
        to_addr = message_payload["message"]["toRecipients"][0]["emailAddress"]["address"]
        domain = to_addr.split("@")[-1] if "@" in to_addr else "unknown"

        if cfg.dry_run:
            logger.info(
                "DRY-RUN Graph send simulated. recipient_domain=%s subject=%r sender=%s",
                domain, message_payload["message"]["subject"], cfg.sender_upn,
            )
            return "dry-run-message-id"

        raise NotImplementedError(
            "Live Graph sendMail HTTP call is intentionally not wired in this build. "
            "Bulk or production email requires explicit human approval per project rules."
        )
