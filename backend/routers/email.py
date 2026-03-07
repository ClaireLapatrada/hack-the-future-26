"""
POST /api/email/draft  — generate a supplier outreach email draft
POST /api/email/send   — send via SMTP (requires SMTP env vars; falls back to draft only)
"""
from __future__ import annotations

import os
import smtplib
import json
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

_PROFILE_PATH = Path(__file__).resolve().parent.parent / "config" / "manufacturer_profile.json"


def _load_profile() -> dict:
    try:
        with open(_PROFILE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


class EmailDraftRequest(BaseModel):
    supplier_name: str
    supplier_contact: str
    disruption_context: str
    ask: str
    # Optional overrides — fall back to company_info from profile
    sender_name: Optional[str] = None
    company_name: Optional[str] = None


class EmailSendRequest(EmailDraftRequest):
    # Additional fields needed for actual send
    to_override: Optional[str] = None  # send to this address instead of supplier_contact


@router.post("/api/email/draft")
def draft_email(body: EmailDraftRequest) -> Dict[str, Any]:
    """Generate a supplier outreach email draft using the action tool."""
    try:
        profile = _load_profile()
        company_info = profile.get("company_info", {})
        sender_name = body.sender_name or company_info.get("sender_name", "Supply Chain Operations Team")
        company_name = body.company_name or company_info.get("company_name", "Our Company")

        from backend.tools.action_tools import draft_supplier_email
        result = draft_supplier_email(
            supplier_name=body.supplier_name,
            supplier_contact=body.supplier_contact,
            disruption_context=body.disruption_context,
            ask=body.ask,
            sender_name=sender_name,
            company_name=company_name,
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/api/email/send")
def send_email(body: EmailSendRequest) -> Dict[str, Any]:
    """
    Draft the email and, if SMTP env vars are configured, send it.
    Required env vars: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM
    Falls back to draft-only if not configured.
    """
    # First draft
    draft_req = EmailDraftRequest(
        supplier_name=body.supplier_name,
        supplier_contact=body.supplier_contact,
        disruption_context=body.disruption_context,
        ask=body.ask,
        sender_name=body.sender_name,
        company_name=body.company_name,
    )
    draft_result = draft_email(draft_req)
    if draft_result.get("status") != "success":
        return draft_result

    draft = draft_result.get("draft_email", {})
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASSWORD")
    smtp_from = os.getenv("SMTP_FROM", smtp_user or "noreply@chainguard.ai")

    to_addr = body.to_override or draft.get("to") or body.supplier_contact

    if not smtp_host or not smtp_user or not smtp_pass:
        return {
            **draft_result,
            "sent": False,
            "send_note": "SMTP not configured — draft only. Set SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD to enable sending.",
        }

    try:
        msg = MIMEText(draft.get("body", ""), "plain")
        msg["Subject"] = draft.get("subject", "Supply Chain Alert")
        msg["From"] = smtp_from
        msg["To"] = to_addr

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_from, [to_addr], msg.as_string())

        return {
            **draft_result,
            "sent": True,
            "sent_to": to_addr,
            "send_note": f"Email sent via SMTP to {to_addr}",
        }
    except Exception as exc:
        return {
            **draft_result,
            "sent": False,
            "send_note": f"SMTP send failed: {exc}. Draft saved.",
        }
