"""
GET /api/dashboard

Returns KPIs, disruption list, supplier risks, operational impact,
revenue-at-risk summary, and mitigation trade-off for the dashboard.

Mirrors ui/app/api/dashboard/route.ts. The computation helpers in this file
are Python ports of the TypeScript lib functions in ui/lib/ (risk-calculation.ts,
operational-impact.ts, revenue-at-risk.ts, mitigation-tradeoff.ts). All logic
is unchanged; only the language and I/O layer differ.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import random
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests
from fastapi import APIRouter, Depends, HTTPException

from backend.data import DataStore, get_data_store
from backend.settings import settings

router = APIRouter()

_SIMULATION_RUNS = 300
_MARGIN_RATE = 0.3
_TIME_HORIZON_DAYS = 30


# Computation helpers (ported from ui/lib/)

def _compute_supplier_risk(supplier: Dict, history: List[Dict], active_disruption: Dict) -> Dict:
    """
    Compute disruption probability for one supplier.
    Matches ui/lib/risk-calculation.ts computeSupplierDisruptionProbability.
    """
    supplier_id = supplier.get("id", "")
    supplier_name = supplier.get("name") or supplier_id
    region = (supplier.get("country") or "Unknown").lower()
    health_score = max(0.0, min(100.0, float(supplier.get("health_score") or 75)))
    single_source = bool(supplier.get("single_source"))
    spend_pct = float(supplier.get("spend_pct") or 0)

    lane_disrupted = False
    lane_severity = "Low"
    for lane_data in (active_disruption.get("shipping_lanes") or {}).values():
        if isinstance(lane_data, dict) and lane_data.get("status") == "DISRUPTED":
            lane_disrupted = True
            lane_severity = lane_data.get("severity") or "High"
            break

    supplier_events = [e for e in history if supplier_id in (e.get("affected_suppliers") or [])]
    delay_events = [
        e for e in supplier_events
        if e.get("impact") and (e["impact"].get("delay_days") or 0) > 0
    ]
    total_events = max(len(supplier_events), 1)
    delivery_delay_frequency = min(1.0, (len(delay_events) / total_events) * 2)

    financial_health_risk = 1 - health_score / 100
    region_instability = 0.2 if any(r in region for r in ("taiwan", "vietnam")) else 0.0
    logistics_congestion = (
        0.7 if lane_disrupted and lane_severity == "High"
        else 0.4 if lane_disrupted
        else 0.0
    )
    weather_disruption_prob = 0.0

    p = (
        0.25 * financial_health_risk
        + 0.25 * region_instability
        + 0.25 * logistics_congestion
        + 0.15 * delivery_delay_frequency
        + 0.10 * weather_disruption_prob
    )
    if single_source:
        p = min(1.0, p * 1.15)
    if spend_pct > 35:
        p = min(1.0, p * 1.10)
    prob_pct = round(p * 100 * 10) / 10

    risk_class = "Low" if prob_pct < 35 else "High" if prob_pct >= 65 else "Medium"

    drivers: List[str] = []
    if financial_health_risk > 0.4:
        drivers.append(f"Supplier financial health score ({round(health_score)}/100)")
    if region_instability > 0.3:
        drivers.append(f"Region instability / geopolitical exposure ({supplier.get('country', 'N/A')})")
    if logistics_congestion > 0.3:
        drivers.append("Logistics congestion / shipping lane disruption")
    if delivery_delay_frequency > 0.3:
        drivers.append(f"Historical delivery delay frequency ({len(delay_events)} events)")
    if single_source:
        drivers.append("Single-source supplier (no qualified backup)")
    if spend_pct > 35:
        drivers.append(f"High spend concentration ({spend_pct}%)")
    if not drivers:
        drivers.append("Baseline risk from profile and history")

    return {
        "supplier_id": supplier_id,
        "supplier_name": supplier_name,
        "time_horizon_days": _TIME_HORIZON_DAYS,
        "disruption_probability_pct": prob_pct,
        "risk_classification": risk_class,
        "primary_drivers": drivers,
        "risk_indicators": {
            "supplier_delivery_delay_frequency": round(delivery_delay_frequency * 1000) / 1000,
            "supplier_financial_health_score": health_score,
            "region_instability_index": round(region_instability * 1000) / 1000,
            "logistics_congestion_score": round(logistics_congestion * 1000) / 1000,
            "weather_disruption_probability": round(weather_disruption_prob * 1000) / 1000,
        },
    }


def _compute_dashboard_risk(suppliers: List[Dict], history: List[Dict], active_disruption: Dict) -> Dict:
    """Aggregate supplier risks. Matches ui/lib/risk-calculation.ts computeDashboardRisk."""
    supplier_risks = [_compute_supplier_risk(s, history, active_disruption) for s in suppliers]
    aggregate = (
        round(max(r["disruption_probability_pct"] for r in supplier_risks))
        if supplier_risks else 0
    )
    return {"supplierRisks": supplier_risks, "aggregateDisruptionRiskPct": aggregate}


def _seeded_rand(seed: int):
    """Simple seeded PRNG matching the TS seededRandom implementation."""
    state = [seed]

    def _next() -> float:
        state[0] = (state[0] * 9301 + 49297) % 233280
        return state[0] / 233280

    return _next


def _compute_operational_impact(
    inventory: List[Dict],
    production_lines: List[Dict],
    suppliers: List[Dict],
    active_disruption: Dict,
) -> Dict:
    """
    Monte Carlo production-downtime estimate.
    Matches ui/lib/operational-impact.ts computeOperationalImpact.
    """
    single_source_ids = {s["id"] for s in suppliers if s.get("single_source")}

    line_to_items: Dict[str, List[Dict]] = {}
    for line in production_lines:
        sem = bool(line.get("semiconductor_dependent"))
        items = [
            inv for inv in inventory
            if (sem and "SEMI" in (inv.get("item_id") or ""))
            or (not sem and "STEEL" in (inv.get("item_id") or ""))
        ]
        line_to_items[line.get("line_id") or ""] = items

    critical_deps: List[Dict] = []
    for line_id, items in line_to_items.items():
        for inv in items:
            critical_deps.append({
                "item_id": inv.get("item_id") or "",
                "supplier_id": inv.get("supplier_id") or "",
                "single_source": inv.get("supplier_id") in single_source_ids,
                "line_id": line_id,
            })

    disruption_active = bool(active_disruption.get("active")) and any(
        (v or {}).get("status") == "DISRUPTED"
        for v in (active_disruption.get("shipping_lanes") or {}).values()
    )

    at_risk_line_ids = {
        d["line_id"] for d in critical_deps
        if d["single_source"] and disruption_active
    }

    delay_min, delay_max = 5, 15
    if active_disruption.get("active") and active_disruption.get("shipping_lanes"):
        delays = [
            v["avg_delay_days"]
            for v in (active_disruption["shipping_lanes"] or {}).values()
            if isinstance(v, dict) and v.get("status") == "DISRUPTED" and isinstance(v.get("avg_delay_days"), (int, float))
        ]
        if delays:
            delay_min = int(min(delays))
            delay_max = int(max(delays))

    rng = _seeded_rand(42)
    shutdown_count = 0
    delay_samples: List[int] = []
    for _ in range(_SIMULATION_RUNS):
        disruption_days = (
            delay_min if delay_min == delay_max
            else delay_min + int(rng() * (delay_max - delay_min + 1))
        )
        delay_samples.append(disruption_days)
        run_shutdown = False
        for line_id in at_risk_line_ids:
            items = line_to_items.get(line_id) or []
            for inv in items:
                if inv.get("supplier_id") not in single_source_ids:
                    continue
                if (inv.get("days_on_hand") or 0) < disruption_days:
                    run_shutdown = True
                    break
            if run_shutdown:
                break
        if run_shutdown:
            shutdown_count += 1

    downtime_pct = round(100 * shutdown_count / _SIMULATION_RUNS)
    affected_lines = [
        {
            "line_id": line.get("line_id") or "",
            "product": line.get("product") or "",
            "daily_revenue_usd": line.get("daily_revenue_usd") or 0,
            "at_risk": (line.get("line_id") or "") in at_risk_line_ids,
        }
        for line in production_lines
    ]

    return {
        "productionDowntimeProbabilityPct": downtime_pct,
        "affectedProductionLines": affected_lines,
        "estimatedDelayDaysMin": min(delay_samples) if delay_samples else delay_min,
        "estimatedDelayDaysMax": max(delay_samples) if delay_samples else delay_max,
        "criticalDependencies": critical_deps,
    }


def _compute_revenue_at_risk_executive(impact: Dict, profile: Dict) -> Dict:
    """
    Revenue-at-risk executive summary.
    Matches ui/lib/revenue-at-risk.ts computeRevenueAtRiskExecutive.
    """
    lines = impact.get("affectedProductionLines") or []
    delay_min = impact.get("estimatedDelayDaysMin") or 5
    delay_max = impact.get("estimatedDelayDaysMax") or 15
    delay_mid = math.floor((delay_min + delay_max) / 2)
    customer_slas = profile.get("customer_slas") or []

    def outcome(delay_days: int) -> Dict:
        rev = sum(
            (line.get("daily_revenue_usd") or 0)
            for line in lines if line.get("at_risk")
        ) * delay_days
        sla = sum((s.get("penalty_per_day_usd") or 0) for s in customer_slas) * delay_days
        margin = rev * _MARGIN_RATE
        return {
            "revenue_at_risk_usd": round(rev * 100) / 100,
            "sla_penalties_usd": round(sla * 100) / 100,
            "margin_impact_usd": round(margin * 100) / 100,
            "delay_days": delay_days,
        }

    best = outcome(delay_min)
    expected = outcome(delay_mid)
    worst = outcome(delay_max)
    rev = expected["revenue_at_risk_usd"]
    margin = expected["margin_impact_usd"]
    sla_pen = expected["sla_penalties_usd"]
    customers = len(customer_slas)

    return {
        "revenueAtRiskUsd": rev,
        "marginImpactUsd": margin,
        "slaPenaltiesUsd": sla_pen,
        "customersAffected": customers,
        "bestCase": best,
        "expectedCase": expected,
        "worstCase": worst,
        "summary": (
            f"Revenue-at-risk: ${rev / 1e6:.1f}M (expected). "
            f"Margin impact: ${margin / 1e6:.1f}M. "
            f"Customers affected: {customers} major OEM accounts. "
            f"SLA penalty exposure: ${sla_pen / 1e3:.0f}K."
        ),
    }


def _compute_mitigation_tradeoff(
    planning_config: Dict,
    disruption_days: int = 10,
    quantity_needed: int = 5000,
    risk_appetite: str = "medium",
) -> Dict:
    """
    Mitigation trade-off summary.
    Matches ui/lib/mitigation-tradeoff.ts computeMitigationTradeoff.
    """
    scenarios = planning_config.get("scenario_definitions") or {}
    weights_map = planning_config.get("risk_appetite_weights") or {}
    weights = weights_map.get(risk_appetite) or weights_map.get("medium") or {"service": 0.45, "cost": 0.35, "speed": 0.2}
    rank_scores = planning_config.get("rank_service_scores") or {"High": 100, "Medium": 60, "Low": 20}

    simulated = []
    for key in ("buffer_build", "alternate_supplier", "airfreight"):
        sc = scenarios.get(key)
        if not sc:
            continue
        premium_unit = sc["base_unit_cost_usd"] * (1 + sc["unit_cost_premium_pct"] / 100)
        variable_cost = premium_unit * quantity_needed
        total_cost = variable_cost + sc["fixed_cost_usd"]
        baseline_cost = sc["base_unit_cost_usd"] * quantity_needed
        incremental_cost = total_cost - baseline_cost

        service_score = rank_scores.get(sc["service_level_protection"], 60)
        cost_score = max(0, 100 - sc["unit_cost_premium_pct"] / 3)
        speed_score = max(0, 100 - sc["implementation_days"] * 3)
        adjusted = service_score * weights["service"] + cost_score * weights["cost"] + speed_score * weights["speed"]

        simulated.append({
            "scenario_type": key,
            "scenario_name": sc["name"],
            "financials": {
                "incremental_cost_usd": incremental_cost,
                "total_cost_usd": total_cost,
                "unit_cost_premium_pct": sc["unit_cost_premium_pct"],
            },
            "timing": {"implementation_days": sc["implementation_days"]},
            "service_level_protection": sc["service_level_protection"],
            "adjusted_score": adjusted,
        })

    simulated.sort(key=lambda x: x["adjusted_score"], reverse=True)
    top = simulated[0] if simulated else None
    recommended = top["scenario_name"] if top else "—"
    svc_impact = top["service_level_protection"] if top else "Medium"

    scenarios_out = [
        {
            "name": r["scenario_name"],
            "costUsd": round(r["financials"]["incremental_cost_usd"] * 100) / 100,
            "serviceLevel": r["service_level_protection"],
            "resilienceNote": (
                "High" if r["service_level_protection"] == "High"
                else "Medium" if r["service_level_protection"] == "Medium"
                else "Lower"
            ),
            "adjustedScore": round(r["adjusted_score"] * 10) / 10,
        }
        for r in simulated
    ]
    cost_vs = [
        f"{r['scenario_name']}: ${r['financials']['incremental_cost_usd'] / 1e3:.0f}K cost, "
        f"{'High' if r['service_level_protection'] == 'High' else 'Medium' if r['service_level_protection'] == 'Medium' else 'Lower'} resilience"
        for r in simulated
    ]

    return {
        "recommendedStrategy": recommended,
        "scenarios": scenarios_out,
        "costVsResilience": cost_vs,
        "serviceLevelImpact": svc_impact,
        "summary": (
            f"Recommended mitigation: {recommended}. "
            f"Cost vs resilience: {'; '.join(cost_vs)}. "
            f"Expected service-level impact: {svc_impact} protection."
        ),
    }


def _fetch_news_disruptions() -> List[Dict]:
    """Call Google CSE for live news. Returns empty list if not configured or on error."""
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

    def _infer_severity(title: str, snippet: str) -> str:
        t = f"{title.lower()} {snippet.lower()}"
        if re.search(r"\b(blockade|closed|halt|critical|crisis|war|attack)\b", t):
            return "CRITICAL"
        if re.search(r"\b(suez|red sea|panama|canal|delay|disruption)\b", t):
            return "HIGH"
        if re.search(r"\b(slow|congestion|shortage|risk)\b", t):
            return "MEDIUM"
        return "LOW"

    items = []
    for it in data.get("items") or []:
        link = it.get("link") or ""
        title = (it.get("title") or "").strip() or "Supply chain disruption"
        snippet = (it.get("snippet") or "").strip()
        severity = _infer_severity(title, snippet)
        items.append({
            "id": f"news-{hashlib.sha1(link.encode()).hexdigest()[:12]}",
            "severity": severity,
            "title": title[:70] + "…" if len(title) > 70 else title,
            "source": it.get("displayLink") or link[:50],
            "url": link,
            "description": snippet or title,
        })
    return items


def _format_age(date_str: str, logged_at: Optional[str] = None) -> str:
    try:
        s = logged_at or date_str
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    except (ValueError, AttributeError):
        return date_str or "—"
    now = datetime.now(timezone.utc)
    diff_s = (now - dt).total_seconds()
    diff_m = math.floor(diff_s / 60)
    diff_h = math.floor(diff_m / 60)
    diff_d = math.floor(diff_h / 24)
    if diff_m < 60:
        return f"{diff_m} min ago"
    if diff_h < 24:
        return f"{diff_h}h ago"
    if diff_d < 30:
        return f"{diff_d}d ago"
    return date_str


@router.get("/api/dashboard")
def get_dashboard(store: DataStore = Depends(get_data_store)) -> Dict[str, Any]:
    """
    Return full dashboard payload: KPIs, disruption list, supplier risks,
    operational impact, revenue-at-risk, and mitigation trade-off.
    """
    real_news = _fetch_news_disruptions()

    profile = store.load_profile()
    erp = store.load_erp()
    history_events = store.load_disruption_history()
    active_disruption = store.load_active_disruption()

    suppliers = [s.model_dump() for s in profile.suppliers]
    production_lines = [l.model_dump() for l in profile.production_lines]
    customer_slas = [c.model_dump() for c in profile.customer_slas]
    inventory = [i.model_dump() for i in (erp.inventory or [])]
    open_pos = erp.open_purchase_orders or []
    disruptions_raw = [d.model_dump() for d in history_events]
    active_raw = active_disruption.model_dump()

    risk_result = _compute_dashboard_risk(suppliers, disruptions_raw, active_raw)
    supplier_risks = risk_result["supplierRisks"]
    aggregate_risk_pct = risk_result["aggregateDisruptionRiskPct"]

    op_impact = _compute_operational_impact(inventory, production_lines, suppliers, active_raw)
    rev_exec = _compute_revenue_at_risk_executive(op_impact, {"customer_slas": customer_slas})

    planning_config: Optional[Dict] = None
    try:
        planning_config = store.load_planning_config()
    except Exception:
        pass
    mitigation_tradeoff = (
        _compute_mitigation_tradeoff(planning_config, 10, 5000, "medium")
        if planning_config
        else None
    )

    single_source_suppliers = [s for s in suppliers if s.get("single_source")]
    max_spend_pct = max((float(s.get("spend_pct") or 0) for s in suppliers), default=0.0)

    if real_news:
        disruption_list = [
            {
                "id": d["id"],
                "severity": d["severity"],
                "title": d["title"],
                "status": "Monitoring",
                "age": "Recent",
            }
            for d in real_news[:20]
        ]
        kpis = {
            "disruptionRisk": aggregate_risk_pct,
            "revenueAtRisk": 0,
            "activeDisruptions": len(real_news),
            "pendingApprovals": 0,
            "overallSupplyRisk": aggregate_risk_pct,
            "logisticsFreight": min(100, len(real_news) * 25),
            "supplierConcentration": min(100, max(0, round(max_spend_pct + len(single_source_suppliers) * 40))),
            "suppliers": len(suppliers),
            "inventoryPolicy": profile.inventory_policy.model_dump() if profile.inventory_policy else None,
            "openPOs": len(open_pos),
            "disruptionRiskTrendPct": 0,
            "revenueTrendPct": 0,
            "activeDisruptionsTrendPct": 0,
            "pendingApprovalsTrendPct": 0,
        }
        return {
            "disruptions": disruption_list,
            "kpis": kpis,
            "supplierRisks": supplier_risks,
            "operationalImpact": op_impact,
            "revenueAtRiskExecutive": rev_exec,
            "mitigationTradeoff": mitigation_tradeoff,
            "allSuppliers": [{"id": s["id"], "name": s["name"]} for s in suppliers],
        }

    # Mock data path
    lanes = active_raw.get("shipping_lanes") or {}
    disrupted_lanes = {
        name: data for name, data in lanes.items()
        if isinstance(data, dict) and data.get("status") == "DISRUPTED"
    }
    initiated_events = [
        {
            "event_id": "initiated-" + re.sub(r"[^a-z0-9-]", "", name.replace(" ", "-").lower()),
            "date": datetime.now(timezone.utc).isoformat()[:10],
            "type": "Shipping Disruption",
            "region": name,
            "severity": data.get("severity") or "High",
            "description": f"{name} disrupted — {data.get('avg_delay_days', 14)} day delay (initiated for demo).",
            "impact": {"delay_days": data.get("avg_delay_days", 14)},
        }
        for name, data in disrupted_lanes.items()
    ] if disrupted_lanes else []

    use_disruptions = active_disruption.active
    effective_disruptions = (
        initiated_events if (use_disruptions and initiated_events)
        else disruptions_raw if use_disruptions
        else []
    )
    active_count = len(effective_disruptions)

    # Pending approvals count
    resolutions: Dict[str, str] = {}
    res_path = settings.approval_resolutions_path
    if res_path.exists():
        try:
            resolutions = json.loads(res_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    pending_from_mock = (
        sum(
            1 for d in disruptions_raw
            if (d.get("mitigation_taken") or {}).get("outcome") == "Pending"
            and d.get("event_id") not in resolutions
        )
        if use_disruptions else 0
    )
    agent_pending = 0
    p_path = settings.pending_approvals_path
    if p_path.exists():
        try:
            raw = json.loads(p_path.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                agent_pending = sum(
                    1 for e in raw
                    if e.get("status") == "pending" or e.get("status") is None
                )
        except Exception:
            pass
    pending_count = pending_from_mock + agent_pending

    total_revenue_at_risk = (
        sum(
            float(d.get("impact", {}).get("revenue_at_risk_usd") or 0)
            for d in disruptions_raw
        )
        if use_disruptions else 0
    )

    logistics_keywords = {"shipping", "suez", "red sea", "canal", "freight", "vessel", "port"}
    logistics_count = sum(
        1 for d in effective_disruptions
        if any(k in ((d.get("type") or "") + (d.get("region") or "") + (d.get("description") or "")).lower()
               for k in logistics_keywords)
    )

    supplier_concentration_score = min(
        100,
        max(0, round(
            max_spend_pct
            + len(single_source_suppliers) * 40
            + (15 if active_disruption.supplier_health_degraded else 0)
        )),
    )

    logistics_freight_score = (
        min(100, round((logistics_count / active_count) * 100)) if active_count > 0 else 0
    )

    disruption_list = [
        {
            "id": d.get("event_id"),
            "severity": (
                "CRITICAL" if str(d.get("severity", "")).upper() == "CRITICAL"
                else "HIGH" if str(d.get("severity", "")).lower() in ("high",)
                else "MEDIUM" if str(d.get("severity", "")).lower() in ("medium",)
                else "LOW"
            ),
            "title": (d.get("description") or "")[:80] + ("…" if len(d.get("description") or "") > 80 else ""),
            "status": "Investigating" if (d.get("mitigation_taken") or {}).get("outcome") == "Pending" else "Mitigating",
            "age": _format_age(d.get("date") or "", d.get("logged_at")),
        }
        for d in effective_disruptions[:20]
    ]

    kpis = {
        "disruptionRisk": aggregate_risk_pct,
        "revenueAtRisk": total_revenue_at_risk,
        "activeDisruptions": active_count,
        "pendingApprovals": pending_count,
        "overallSupplyRisk": aggregate_risk_pct,
        "logisticsFreight": logistics_freight_score,
        "supplierConcentration": supplier_concentration_score,
        "suppliers": len(suppliers),
        "inventoryPolicy": profile.inventory_policy.model_dump() if profile.inventory_policy else None,
        "openPOs": len(open_pos),
        "disruptionRiskTrendPct": min(15, 5 + pending_count * 4) if pending_count > 0 else 0,
        "revenueTrendPct": min(15, 5 + math.floor(total_revenue_at_risk / 500_000)) if total_revenue_at_risk > 0 else 0,
        "activeDisruptionsTrendPct": 0,
        "pendingApprovalsTrendPct": 0,
    }

    return {
        "disruptions": disruption_list,
        "kpis": kpis,
        "supplierRisks": supplier_risks,
        "operationalImpact": op_impact,
        "revenueAtRiskExecutive": rev_exec,
        "mitigationTradeoff": mitigation_tradeoff,
        "allSuppliers": [{"id": s["id"], "name": s["name"]} for s in suppliers],
    }
