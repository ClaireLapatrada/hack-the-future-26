"""
GET  /api/approvals         — list pending approvals
PATCH /api/approvals/{id}   — approve or reject an approval

Mirrors the logic in ui/app/api/approvals/route.ts, using DataStore for
all file I/O instead of ad-hoc fs calls.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from math import floor
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel

from backend.data import DataStore, get_data_store
from backend.models.approvals import ApprovalEntry, ApprovalStatus
from backend.settings import settings

router = APIRouter()


# Response shapes the UI expects

class ApprovalItem(BaseModel):
    id: str
    severity: Literal["CRITICAL", "HIGH", "MEDIUM"]
    title: str
    age: str
    situation: str
    recommendation: str
    confidence: str
    auditLog: List[Dict[str, Any]]


class PatchApprovalBody(BaseModel):
    id: str
    action: Literal["approve", "reject"]


def _format_age(date_str: str) -> str:
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return "—"
    now = datetime.now(timezone.utc)
    diff_s = (now - dt).total_seconds()
    diff_m = floor(diff_s / 60)
    diff_h = floor(diff_m / 60)
    if diff_m < 60:
        return f"{diff_m} min ago"
    if diff_h < 24:
        return f"{diff_h}h ago"
    return f"{floor(diff_h / 24)}d ago"


def _normalize_severity(s: str) -> Literal["CRITICAL", "HIGH", "MEDIUM"]:
    u = (s or "").upper()
    if u == "CRITICAL":
        return "CRITICAL"
    if u == "HIGH":
        return "HIGH"
    return "MEDIUM"


@router.get("/api/approvals", response_model=List[ApprovalItem])
def list_approvals(store: DataStore = Depends(get_data_store)) -> List[ApprovalItem]:
    """
    Return pending approvals in display order (APPR-* newest first, then EVT-*).

    Sources:
      1. Agent-generated entries from pending_approvals.json (status == pending or missing).
      2. Mock disruption history entries whose mitigation outcome is "Pending" and not yet resolved.
    """
    items: List[ApprovalItem] = []

    # 1. Agent-generated pending approvals
    try:
        raw_approvals = store.load_pending_approvals()
        for entry in raw_approvals:
            if entry.status not in (ApprovalStatus.pending, None):
                continue
            items.append(ApprovalItem(
                id=entry.id,
                severity=_normalize_severity(entry.severity),
                title=entry.title,
                age=_format_age(entry.createdAt or ""),
                situation=entry.situation,
                recommendation=entry.recommendation,
                confidence=entry.confidence or "90%",
                auditLog=entry.auditLog or [],
            ))
    except Exception:
        pass

    # 2. Mock disruption history — Pending outcome entries not yet resolved
    resolutions: Dict[str, str] = {}
    res_path = settings.approval_resolutions_path
    if res_path.exists():
        try:
            resolutions = json.loads(res_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    try:
        disruptions = store.load_disruption_history()
        for d in disruptions:
            if not (d.mitigation_taken and d.mitigation_taken.outcome == "Pending"):
                continue
            if d.event_id in resolutions:
                continue
            action = d.mitigation_taken.action if d.mitigation_taken else "Pending"
            rev = d.impact.revenue_at_risk_usd if d.impact else None
            impact_str = f"Revenue at risk: ${rev / 1_000_000:.2f}M. " if rev else ""
            items.append(ApprovalItem(
                id=d.event_id,
                severity=_normalize_severity(d.severity),
                title=f"{d.type} — {d.region}",
                age=_format_age(d.logged_at or d.date),
                situation=f"{impact_str}{d.description}",
                recommendation=f"APPROVE — {action}",
                confidence="90%",
                auditLog=[
                    {"time": "—", "text": d.description},
                    {"time": "—", "text": action},
                ],
            ))
    except Exception:
        pass

    # Deduplicate
    seen: set = set()
    unique: List[ApprovalItem] = []
    for item in items:
        if item.id not in seen:
            seen.add(item.id)
            unique.append(item)

    # Sort: APPR-* newest first, then EVT-*
    unique.sort(
        key=lambda a: (
            0 if a.id.startswith("APPR-") else 1,
            [-ord(c) for c in a.id],
        )
    )

    return unique


@router.patch("/api/approvals/{approval_id}")
def update_approval(
    approval_id: str,
    body: PatchApprovalBody = Body(...),
    store: DataStore = Depends(get_data_store),
) -> Dict[str, Any]:
    """
    Approve or reject an approval by ID.

    APPR-* / RST-*: updates status in pending_approvals.json.
    EVT-*: records resolution in approval_resolutions.json.
    """
    id_ = body.id.strip()
    action = body.action

    if not id_ or id_ != approval_id:
        raise HTTPException(status_code=400, detail="ID mismatch between URL and body")

    if id_.startswith("APPR-") or id_.startswith("RST-"):
        approvals = store.load_pending_approvals()
        # Find pending entry first, then fall back to any match
        idx = next(
            (i for i, e in enumerate(approvals) if e.id == id_ and e.status == ApprovalStatus.pending),
            None,
        )
        if idx is None:
            idx = next((i for i, e in enumerate(approvals) if e.id == id_), None)
        if idx is None:
            raise HTTPException(status_code=404, detail="Approval not found")
        approvals[idx].status = ApprovalStatus.approved if action == "approve" else ApprovalStatus.rejected
        store.save_pending_approvals(approvals)
        return {"ok": True, "id": id_, "status": approvals[idx].status.value}

    if id_.startswith("EVT-"):
        res_path = settings.approval_resolutions_path
        resolutions: Dict[str, str] = {}
        if res_path.exists():
            try:
                resolutions = json.loads(res_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        resolutions[id_] = "approved" if action == "approve" else "rejected"
        res_path.parent.mkdir(parents=True, exist_ok=True)
        res_path.write_text(json.dumps(resolutions, indent=2), encoding="utf-8")
        return {"ok": True, "id": id_, "status": resolutions[id_]}

    raise HTTPException(status_code=400, detail="Unknown approval id format")
