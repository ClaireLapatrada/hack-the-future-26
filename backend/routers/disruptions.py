"""
GET /api/disruptions

Returns disruption items for the disruptions UI page.

Priority order (mirrors ui/app/api/disruptions/route.ts):
  1. Live news from Google CSE — if any results, return them.
  2. Active disruption config — if active and lanes are DISRUPTED, synthesise items.
  3. Fall back to mock disruption history.
"""
from __future__ import annotations

import hashlib
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

import requests
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.data import DataStore, get_data_store

router = APIRouter()

SeverityLiteral = Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]


class TimelineEntry(BaseModel):
    time: str
    text: str
    muted: Optional[bool] = None


class DisruptionItem(BaseModel):
    id: str
    impact: str
    severity: SeverityLiteral
    title: str
    tags: List[str]
    description: str
    timeline: List[TimelineEntry]
    source: Optional[str] = None
    url: Optional[str] = None


def _hash_id(url: str) -> str:
    return hashlib.sha1(url.encode()).hexdigest()[:12]


def _infer_severity(title: str, snippet: str) -> SeverityLiteral:
    t = f"{title.lower()} {snippet.lower()}"
    if re.search(r"\b(blockade|closed|halt|critical|crisis|war|attack)\b", t):
        return "CRITICAL"
    if re.search(r"\b(suez|red sea|panama|canal|delay|disruption)\b", t):
        return "HIGH"
    if re.search(r"\b(slow|congestion|shortage|risk)\b", t):
        return "MEDIUM"
    return "LOW"


def _format_time(iso_str: str) -> str:
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%H:%M:%S")
    except (ValueError, AttributeError):
        return iso_str


def _format_display_time(iso_str: str) -> str:
    """Format ISO timestamp as 'YYYY-MM-DD HH:MM:SS'."""
    if not iso_str:
        return "—"
    try:
        d = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return d.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, AttributeError):
        return iso_str


def _fetch_news_disruptions() -> List[DisruptionItem]:
    """Call Google CSE and return disruption items. Returns empty list if not configured."""
    api_key = os.getenv("GOOGLE_SEARCH_API_KEY") or os.getenv("GOOGLE_API_KEY")
    cx = os.getenv("GOOGLE_SEARCH_ENGINE_ID")
    if not api_key or not cx:
        return []
    try:
        resp = requests.get(
            "https://www.googleapis.com/customsearch/v1",
            params={"key": api_key, "cx": cx, "q": "supply chain disruption shipping 2025", "num": 10},
            timeout=15,
        )
        if not resp.ok:
            return []
        data = resp.json()
    except Exception:
        return []

    items: List[DisruptionItem] = []
    for it in data.get("items") or []:
        link = it.get("link") or ""
        title = (it.get("title") or "").strip() or "Supply chain disruption"
        snippet = (it.get("snippet") or "").strip()
        meta = ((it.get("pagemap") or {}).get("metatags") or [{}])[0]
        published = (
            meta.get("article:published_time")
            or meta.get("datePublished")
            or meta.get("pubdate")
            or meta.get("date")
            or datetime.now(timezone.utc).isoformat()
        )
        severity = _infer_severity(title, snippet)
        combined = f"{title} {snippet}"
        tags: List[str] = []
        if re.search(r"\bshipping\b", combined, re.I):
            tags.append("Shipping")
        if re.search(r"\bsuez|red sea|panama|canal\b", combined, re.I):
            tags.append("Maritime")
        if re.search(r"\bsupply chain\b", combined, re.I):
            tags.append("Supply Chain")
        if not tags:
            tags.append("News")
        display_title = title[:70] + "…" if len(title) > 70 else title
        items.append(DisruptionItem(
            id=f"news-{_hash_id(link)}",
            impact="—",
            severity=severity,
            title=display_title,
            tags=tags,
            description=snippet or title,
            timeline=[TimelineEntry(time=_format_time(published), text=snippet or title)],
            source=it.get("displayLink") or link[:50],
            url=link,
        ))
    return items


def _to_severity(s: str) -> SeverityLiteral:
    u = (s or "").upper()
    if u == "CRITICAL":
        return "CRITICAL"
    if u == "HIGH":
        return "HIGH"
    if u == "MEDIUM":
        return "MEDIUM"
    return "LOW"


def _format_impact(impact: Any) -> str:
    rev = (impact or {}).get("revenue_at_risk_usd") if isinstance(impact, dict) else None
    if rev is None:
        try:
            rev = impact.revenue_at_risk_usd
        except AttributeError:
            pass
    if rev is not None and isinstance(rev, (int, float)):
        if rev >= 1_000_000:
            return f"${rev / 1_000_000:.1f}M"
        if rev >= 1_000:
            return f"${rev / 1_000:.0f}K"
        return f"${rev}"
    return "—"


@router.get("/api/disruptions", response_model=List[DisruptionItem])
def get_disruptions(store: DataStore = Depends(get_data_store)) -> List[DisruptionItem]:
    """
    Return disruption items for display.

    Tries live Google news first. If empty, falls back to active disruption
    config, then to mock disruption history.
    """
    # 1. Live news
    real_items = _fetch_news_disruptions()
    if real_items:
        return real_items

    # 2. Active disruption config
    active = store.load_active_disruption()
    if not active.active:
        return []

    lanes = active.shipping_lanes or {}
    disrupted = {name: data for name, data in lanes.items() if data.status == "DISRUPTED"}
    if disrupted:
        now = datetime.now(timezone.utc).isoformat()
        items: List[DisruptionItem] = []
        for lane_name, data in disrupted.items():
            delay_days = data.avg_delay_days or 14
            sev_str = (data.severity or "High").upper()
            sev: SeverityLiteral = (
                "CRITICAL" if sev_str == "CRITICAL"
                else "HIGH" if sev_str == "HIGH"
                else "MEDIUM" if sev_str == "MEDIUM"
                else "LOW"
            )
            slug = re.sub(r"[^a-z0-9-]", "", lane_name.replace(" ", "-").lower())
            reroute_note = f" Reroute via {data.reroute_via}." if data.reroute_via else ""
            items.append(DisruptionItem(
                id=f"initiated-{slug}",
                impact=f"{delay_days}d delay",
                severity=sev,
                title=f"{lane_name} — disrupted ({delay_days} day delay)",
                tags=["Shipping", lane_name, "Initiated"],
                description=(
                    f"Lane {lane_name} is reported disrupted with estimated {delay_days}-day delay."
                    f"{reroute_note} Initiated via scripts/initiate_event.py for demo."
                ),
                timeline=[TimelineEntry(
                    time=_format_display_time(now),
                    text=f"Disruption initiated: {lane_name} — {delay_days} day(s) delay.",
                )],
            ))
        return items

    # 3. Fallback: mock disruption history
    disruptions = store.load_disruption_history()
    result: List[DisruptionItem] = []
    for d in disruptions:
        desc = d.description or ""
        timeline_entries: List[TimelineEntry] = []
        if d.timeline:
            for te in d.timeline:
                t = te.get("time", "—") if isinstance(te, dict) else getattr(te, "time", "—")
                text = te.get("text", "") if isinstance(te, dict) else getattr(te, "text", "")
                muted = te.get("muted") if isinstance(te, dict) else getattr(te, "muted", None)
                timeline_entries.append(TimelineEntry(time=t, text=text, muted=muted))
        else:
            t0 = d.logged_at or d.date
            try:
                datetime.fromisoformat(t0.replace("Z", "+00:00"))
                t_str = _format_display_time(t0)
            except Exception:
                t_str = t0 or "—"
            timeline_entries.append(TimelineEntry(time=t_str, text=desc))
            if d.mitigation_taken and d.mitigation_taken.action:
                timeline_entries.append(TimelineEntry(time=t_str, text=f"Mitigation: {d.mitigation_taken.action}", muted=True))
            if d.lessons_learned:
                timeline_entries.append(TimelineEntry(time=t_str, text=d.lessons_learned, muted=True))
        if not timeline_entries:
            timeline_entries.append(TimelineEntry(time="—", text="No timeline data."))

        impact_val = d.impact.model_dump() if d.impact else {}
        result.append(DisruptionItem(
            id=d.event_id,
            impact=_format_impact(impact_val),
            severity=_to_severity(d.severity),
            title=(desc[:70] + "…") if len(desc) > 70 else desc,
            tags=[t for t in [d.type, d.region] if t],
            description=desc,
            timeline=timeline_entries,
        ))
    return result
