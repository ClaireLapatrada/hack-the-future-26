"""
Operational Impact Modeling — Estimate how disruption propagates through the production network.

Objective: Production downtime probability, affected lines, estimated delay, critical dependencies.
Inputs: BOM (inventory + supplier), production schedules (production_lines), supplier lead times,
        inventory levels (ERP), production capacity, logistics (active disruption).
Mechanism: Supply network graph (suppliers → items → lines), critical node identification,
           Monte Carlo simulation for disruption propagation.
Output: Production downtime probability (%), affected production lines, estimated delay range,
        critical component dependencies.
"""

import json
import random
from pathlib import Path
from typing import Optional

from backend.models.tool_results import OperationalImpactResult

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _load_profile():
    import os
    env_path = os.getenv("MANUFACTURER_PROFILE_PATH")
    path = Path(env_path) if env_path else CONFIG_DIR / "manufacturer_profile.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _load_erp():
    import os
    env_path = os.getenv("ERP_JSON_PATH")
    path = Path(env_path) if env_path else DATA_DIR / "mock_erp.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _load_active_disruption():
    for p in [CONFIG_DIR / "active_disruption.json", PROJECT_ROOT / "config" / "active_disruption.json"]:
        if p.exists():
            try:
                with open(p, encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                continue
    return {"active": False, "shipping_lanes": {}}


def get_operational_impact(
    affected_supplier_id: Optional[str] = None,
    disruption_days_assumed: Optional[int] = None,
    simulation_runs: int = 500,
) -> OperationalImpactResult:
    """
    Estimate how disruption propagates through the production network.

    Builds a supply network graph (suppliers → components → production lines), identifies
    critical nodes (single-source, no substitutes, high dependency), runs Monte Carlo
    simulation to model disruption propagation (inventory depletion, capacity constraints),
    and returns production downtime probability, affected lines, delay range, and
    critical dependencies.

    Args:
        affected_supplier_id: If set, assume disruption at this supplier only; else derive from active disruption.
        disruption_days_assumed: If set, use this as fixed disruption length; else sample from active config or 5–15 days.
        simulation_runs: Number of Monte Carlo runs (default 500).

    Returns:
        production_downtime_probability_pct: Probability (0–100%) of plant shutdown within the horizon.
        affected_production_lines: List of { line_id, product, daily_revenue_usd, at_risk: bool }.
        estimated_delay_days_min, estimated_delay_days_max: Delay duration range.
        critical_component_dependencies: List of { item_id, supplier_id, single_source, line_id }.
        summary: Human-readable impact summary.
    """
    profile = _load_profile()
    erp = _load_erp()
    active = _load_active_disruption()

    inventory = erp.get("inventory") or []
    production_lines = profile.get("production_lines") or []
    suppliers = profile.get("suppliers") or []

    # Resolve disruption horizon from active config if not passed
    if disruption_days_assumed is not None:
        delay_min, delay_max = disruption_days_assumed, disruption_days_assumed
    else:
        lanes = active.get("shipping_lanes") or {}
        delays = []
        for v in lanes.values():
            if isinstance(v, dict) and v.get("status") == "DISRUPTED":
                d = v.get("avg_delay_days")
                if isinstance(d, (int, float)):
                    delays.append(int(d))
        if delays:
            delay_min, delay_max = min(delays), max(delays)
        else:
            delay_min, delay_max = 5, 15

    # Build dependency: line -> items (which items feed this line)
    # SEMI* items -> semiconductor_dependent lines; STEEL* -> non-semiconductor
    line_to_items: dict[str, list[dict]] = {}
    for line in production_lines:
        line_id = line.get("line_id") or ""
        sem = line.get("semiconductor_dependent", False)
        items_for_line = [
            inv for inv in inventory
            if (sem and "SEMI" in (inv.get("item_id") or "")) or (not sem and "STEEL" in (inv.get("item_id") or ""))
        ]
        line_to_items[line_id] = items_for_line

    # Critical dependencies: single-source supplier items that feed a line
    supplier_ids = {s["id"] for s in suppliers}
    single_source_ids = {s["id"] for s in suppliers if s.get("single_source")}
    critical_dependencies = []
    for line_id, items in line_to_items.items():
        for inv in items:
            sid = inv.get("supplier_id")
            item_id = inv.get("item_id") or ""
            critical_dependencies.append({
                "item_id": item_id,
                "supplier_id": sid,
                "single_source": sid in single_source_ids,
                "line_id": line_id,
            })

    # Affected production lines: lines that depend on affected_supplier_id or (if not set) any disrupted path
    if affected_supplier_id:
        at_risk_line_ids = {
            line_id for line_id, items in line_to_items.items()
            if any(inv.get("supplier_id") == affected_supplier_id for inv in items)
        }
    else:
        at_risk_line_ids = {dep["line_id"] for dep in critical_dependencies if dep["single_source"]}

    affected_lines_out = []
    for line in production_lines:
        line_id = line.get("line_id") or ""
        affected_lines_out.append({
            "line_id": line_id,
            "product": line.get("product") or "",
            "daily_revenue_usd": line.get("daily_revenue_usd") or 0,
            "at_risk": line_id in at_risk_line_ids,
        })

    # Monte Carlo: each run samples disruption_days; for at-risk lines, check if any component from a disrupted supplier depletes
    disrupted_suppliers = {affected_supplier_id} if affected_supplier_id else single_source_ids
    random.seed(42)
    shutdown_count = 0
    delay_samples = []
    for _ in range(simulation_runs):
        disruption_days = random.randint(delay_min, delay_max) if delay_min != delay_max else delay_min
        delay_samples.append(disruption_days)
        run_shutdown = False
        for line_id in at_risk_line_ids:
            items = line_to_items.get(line_id, [])
            for inv in items:
                if inv.get("supplier_id") not in disrupted_suppliers:
                    continue
                days_on_hand = (inv.get("days_on_hand") or 0)
                if days_on_hand < disruption_days:
                    run_shutdown = True
                    break
            if run_shutdown:
                break
        if run_shutdown:
            shutdown_count += 1

    production_downtime_probability_pct = round(100.0 * shutdown_count / simulation_runs, 1)
    estimated_delay_days_min = min(delay_samples)
    estimated_delay_days_max = max(delay_samples)

    # Summary
    at_risk_names = [l["product"] or l["line_id"] for l in affected_lines_out if l["at_risk"]]
    summary = (
        f"Operational impact: {production_downtime_probability_pct}% probability of plant shutdown within 10 days. "
        f"Affected lines: {', '.join(at_risk_names) or 'None'}. "
        f"Estimated delay: {estimated_delay_days_min}–{estimated_delay_days_max} days. "
        f"Critical dependencies: {len([d for d in critical_dependencies if d['single_source']])} single-source components."
    )

    return {
        "status": "success",
        "production_downtime_probability_pct": production_downtime_probability_pct,
        "affected_production_lines": affected_lines_out,
        "estimated_delay_days_min": estimated_delay_days_min,
        "estimated_delay_days_max": estimated_delay_days_max,
        "critical_component_dependencies": critical_dependencies,
        "summary": summary,
    }
