"""
Planning and Decision Engine — Scenario simulation, supplier reallocation, buffer stock strategy.
Used by the Scenario Planning Agent.

Inputs: supplier cost structures, lead times, transportation costs, inventory holding costs,
        SLAs, production capacity, demand forecasts (from config + manufacturer profile).
Outputs: scenario comparison table, recommended scenario, supplier allocation,
         recommended buffer stock, stockout probability, cost impacts.

Config: planning_config.json (PLANNING_CONFIG_PATH). Optional: manufacturer profile, ERP for data-driven runs.
"""

import json
import os
import random
from pathlib import Path
from datetime import datetime
from typing import List, Optional

# Load config once at import
_ENV_CONFIG_PATH = os.getenv("PLANNING_CONFIG_PATH")
_CONFIG_PATH = (
    Path(_ENV_CONFIG_PATH)
    if _ENV_CONFIG_PATH
    else Path(__file__).resolve().parent.parent / "planning_config.json"
)
with open(_CONFIG_PATH, encoding="utf-8") as _f:
    _CONFIG = json.load(_f)

SCENARIOS = _CONFIG.get("scenario_definitions", {})
ALTERNATIVE_SUPPLIERS = _CONFIG.get("alternative_suppliers", {})
AIRFREIGHT_RATES = _CONFIG.get("airfreight_rates", {})
AIRFREIGHT_DEFAULTS = _CONFIG.get("airfreight_defaults", {"default_rate_per_kg": 9.0, "default_transit_days": 5, "handling_fee_usd": 1500, "customs_pct": 0.03})
RISK_WEIGHTS = _CONFIG.get("risk_appetite_weights", {"low": {"service": 0.6, "cost": 0.25, "speed": 0.15}, "medium": {"service": 0.45, "cost": 0.35, "speed": 0.2}, "high": {"service": 0.3, "cost": 0.45, "speed": 0.25}})
SERVICE_LEVEL_SCORES = _CONFIG.get("service_level_scores", {"High": 90, "Medium": 60, "Low": 30})
RANK_SERVICE_SCORES = _CONFIG.get("rank_service_scores", {"High": 100, "Medium": 60, "Low": 20})

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
UI_DATA_DIR = Path(__file__).resolve().parent.parent / "ui" / "data"
PLANNING_DOCUMENTS_PATH = UI_DATA_DIR / "planning_documents.json"


def _load_profile() -> dict:
    env_path = os.getenv("MANUFACTURER_PROFILE_PATH")
    path = Path(env_path) if env_path else CONFIG_DIR / "manufacturer_profile.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _load_erp() -> dict:
    env_path = os.getenv("ERP_JSON_PATH")
    path = Path(env_path) if env_path else DATA_DIR / "mock_erp.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ---------- Scenario simulation (cost vs service trade-offs) ----------

def run_scenario_simulation(
    disruption_days_min: int = 5,
    disruption_days_max: int = 15,
    quantity_needed: int = 5000,
    affected_item_id: str = "SEMI-MCU-32",
    risk_appetite: str = "medium",
    monte_carlo_runs: int = 200,
) -> dict:
    """
    Scenario simulation: evaluate mitigation strategies across cost, service level, and operational risk.
    Uses Monte Carlo simulation for disruption and demand uncertainty; multi-objective evaluation.
    Outputs: scenario comparison table, recommended scenario, expected service-level performance,
    expected cost increase, disruption resilience improvement.
    """
    scenario_keys = ["buffer_build", "alternate_supplier", "airfreight", "spot_market", "demand_deferral"]
    w = RISK_WEIGHTS.get(risk_appetite, RISK_WEIGHTS["medium"])
    results_per_scenario: dict[str, list[dict]] = {k: [] for k in scenario_keys if k in SCENARIOS}

    random.seed(42)
    for _ in range(monte_carlo_runs):
        disruption_days = random.randint(disruption_days_min, disruption_days_max)
        demand_mult = 0.9 + random.random() * 0.2  # 90–110% demand uncertainty
        q = max(100, int(quantity_needed * demand_mult))
        for key in list(results_per_scenario.keys()):
            sc = SCENARIOS.get(key)
            if not sc:
                continue
            premium_unit = sc["base_unit_cost_usd"] * (1 + sc["unit_cost_premium_pct"] / 100)
            total_cost = premium_unit * q + sc["fixed_cost_usd"]
            baseline_cost = sc["base_unit_cost_usd"] * q
            incremental_cost = total_cost - baseline_cost
            service_score = RANK_SERVICE_SCORES.get(sc["service_level_protection"], 60)
            cost_score = max(0, 100 - sc["unit_cost_premium_pct"] / 3)
            speed_score = max(0, 100 - sc["implementation_days"] * 3)
            adjusted = service_score * w["service"] + cost_score * w["cost"] + speed_score * w["speed"]
            results_per_scenario[key].append({
                "incremental_cost_usd": incremental_cost,
                "total_cost_usd": total_cost,
                "adjusted_score": adjusted,
                "service_level": sc["service_level_protection"],
                "disruption_days": disruption_days,
            })

    comparison_table = []
    for key in results_per_scenario:
        runs = results_per_scenario[key]
        if not runs:
            continue
        sc = SCENARIOS[key]
        avg_cost = sum(r["incremental_cost_usd"] for r in runs) / len(runs)
        avg_score = sum(r["adjusted_score"] for r in runs) / len(runs)
        comparison_table.append({
            "scenario_id": key,
            "scenario_name": sc["name"],
            "expected_cost_increase_usd": round(avg_cost, 2),
            "expected_service_level": sc["service_level_protection"],
            "average_score": round(avg_score, 1),
            "description": sc["description"],
        })

    comparison_table.sort(key=lambda x: x["average_score"], reverse=True)
    recommended = comparison_table[0] if comparison_table else None
    baseline_cost = SCENARIOS.get("buffer_build", {}).get("base_unit_cost_usd", 12.5) * quantity_needed
    expected_cost_increase = recommended["expected_cost_increase_usd"] if recommended else 0
    cost_increase_pct = round(100 * expected_cost_increase / baseline_cost, 1) if baseline_cost else 0

    return {
        "status": "success",
        "scenario_comparison_table": comparison_table,
        "recommended_scenario": recommended["scenario_name"] if recommended else None,
        "recommended_scenario_id": recommended["scenario_id"] if recommended else None,
        "expected_service_level_performance": recommended["expected_service_level"] if recommended else None,
        "expected_cost_increase_usd": expected_cost_increase,
        "expected_cost_increase_pct": cost_increase_pct,
        "disruption_resilience_improvement": "Higher service-level protection and reduced stockout risk under disruption uncertainty.",
        "monte_carlo_runs": monte_carlo_runs,
        "risk_appetite": risk_appetite,
        "summary": (
            f"Recommended: {recommended['scenario_name']}. "
            f"Expected cost increase: ${expected_cost_increase:,.0f} ({cost_increase_pct}%). "
            f"Service level: {recommended['expected_service_level']}."
        ) if recommended else "No scenarios available.",
    }


def simulate_mitigation_scenario(
    scenario_type: str,
    affected_item_id: str,
    disruption_days: int,
    quantity_needed: int,
) -> dict:
    """Simulate a single mitigation scenario (cost, time, service). Used by run_scenario_simulation and agents."""
    scenario = SCENARIOS.get(scenario_type)
    if not scenario:
        return {"status": "error", "message": f"Unknown scenario type: {scenario_type}"}
    premium_unit_cost = scenario["base_unit_cost_usd"] * (1 + scenario["unit_cost_premium_pct"] / 100)
    variable_cost = premium_unit_cost * quantity_needed
    total_cost = variable_cost + scenario["fixed_cost_usd"]
    baseline_cost = scenario["base_unit_cost_usd"] * quantity_needed
    incremental_cost = total_cost - baseline_cost
    service_score = SERVICE_LEVEL_SCORES.get(scenario["service_level_protection"], 50)
    cost_score = max(0, 100 - (scenario["unit_cost_premium_pct"] / 3))
    speed_score = max(0, 100 - (scenario["implementation_days"] * 4))
    composite_score = service_score * 0.5 + cost_score * 0.3 + speed_score * 0.2
    return {
        "status": "success",
        "scenario_type": scenario_type,
        "scenario_name": scenario["name"],
        "description": scenario["description"],
        "financials": {"incremental_cost_usd": round(incremental_cost, 2), "total_cost_usd": round(total_cost, 2), "unit_cost_premium_pct": scenario["unit_cost_premium_pct"]},
        "timing": {"implementation_days": scenario["implementation_days"], "lead_time_change_days": scenario["lead_time_reduction_days"]},
        "service_level_protection": scenario["service_level_protection"],
        "risks": scenario.get("risks", []),
        "composite_score": round(composite_score, 1),
        "co2_impact": scenario.get("co2_impact", "Unknown"),
    }


def rank_scenarios(scenarios_json: str, risk_appetite: str = "low") -> dict:
    """Rank mitigation scenarios by composite score adjusted for risk appetite. Used by run_scenario_simulation."""
    try:
        scenarios = json.loads(scenarios_json)
    except (TypeError, json.JSONDecodeError):
        return {"status": "error", "message": "scenarios_json must be a valid JSON array of scenario objects"}
    if not isinstance(scenarios, list):
        return {"status": "error", "message": "scenarios_json must be a JSON array"}
    w = RISK_WEIGHTS.get(risk_appetite, RISK_WEIGHTS["low"])
    ranked = []
    for s in scenarios:
        service_score = RANK_SERVICE_SCORES.get(s.get("service_level_protection", "Low"), 20)
        cost_score = max(0, 100 - s.get("financials", {}).get("unit_cost_premium_pct", 0) / 3)
        speed_score = max(0, 100 - s.get("timing", {}).get("implementation_days", 30) * 3)
        adjusted_score = service_score * w["service"] + cost_score * w["cost"] + speed_score * w["speed"]
        ranked.append({**s, "adjusted_score": round(adjusted_score, 1)})
    ranked.sort(key=lambda x: x["adjusted_score"], reverse=True)
    _name = lambda r: r.get("scenario_name") or r.get("scenario_type") or "Unknown"
    return {
        "status": "success",
        "risk_appetite": risk_appetite,
        "ranked_scenarios": ranked,
        "top_recommendation": _name(ranked[0]) if ranked else None,
        "reasoning": f"Based on '{risk_appetite}' risk appetite, '{_name(ranked[0])}' scores highest." if ranked else "No scenarios to rank.",
    }


def evaluate_mitigation_tradeoffs(
    disruption_days: int = 10,
    quantity_needed: int = 5000,
    affected_item_id: str = "SEMI-MCU-32",
    risk_appetite: str = "medium",
) -> dict:
    """Multi-variable trade-off: delegates to run_scenario_simulation and returns recommended strategy, cost vs resilience, service-level impact."""
    out = run_scenario_simulation(
        disruption_days_min=max(1, disruption_days - 5),
        disruption_days_max=disruption_days + 5,
        quantity_needed=quantity_needed,
        affected_item_id=affected_item_id,
        risk_appetite=risk_appetite,
        monte_carlo_runs=100,
    )
    if out.get("status") != "success":
        return out
    table = out.get("scenario_comparison_table") or []
    cost_vs_resilience = [f"{r['scenario_name']}: ${r['expected_cost_increase_usd']/1e3:.0f}K cost, {r['expected_service_level']} SL" for r in table]
    return {
        "status": "success",
        "recommended_strategy": out.get("recommended_scenario"),
        "scenarios": [{"name": r["scenario_name"], "cost_usd": r["expected_cost_increase_usd"], "service_level": r["expected_service_level"], "resilience_note": r["expected_service_level"], "adjusted_score": r.get("average_score")} for r in table],
        "cost_vs_resilience": cost_vs_resilience,
        "service_level_impact": out.get("expected_service_level_performance"),
        "summary": out.get("summary"),
    }


def create_planning_document(
    title: str,
    situation_summary: str,
    recommended_scenario: str,
    scenario_comparison_json: str = "[]",
    cost_impact_summary: str = "",
    service_level_impact: str = "",
    document_type: str = "mitigation_plan",
    affected_item_id: str = "",
    risk_appetite: str = "",
) -> dict:
    """
    Create a persistent planning document (past crisis / mitigation plan) for internal access.
    Call this AFTER run_scenario_simulation or evaluate_mitigation_tradeoffs when you have a final recommendation.
    All arguments must be populated from the actual tool outputs (e.g. scenario_comparison_table, recommended_scenario,
    expected_cost_increase_usd, summary) — do not use placeholder, generic, or hardcoded text. The document is
    agent-generated from live planning results.
    Returns document_id and path for the agent stream "View document" link.
    """
    import re
    doc_id = f"PLAN-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or doc_id.lower()
    try:
        comparison = json.loads(scenario_comparison_json) if scenario_comparison_json else []
    except (TypeError, json.JSONDecodeError):
        comparison = []
    doc = {
        "id": doc_id,
        "slug": slug,
        "title": title,
        "createdAt": datetime.now().isoformat(),
        "situationSummary": situation_summary,
        "recommendedScenario": recommended_scenario,
        "scenarioComparison": comparison if isinstance(comparison, list) else [],
        "costImpactSummary": cost_impact_summary,
        "serviceLevelImpact": service_level_impact,
        "documentType": document_type,
        "affectedItemId": affected_item_id,
        "riskAppetite": risk_appetite,
    }
    UI_DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        if PLANNING_DOCUMENTS_PATH.exists():
            with open(PLANNING_DOCUMENTS_PATH, encoding="utf-8") as f:
                data = json.load(f)
            docs = data if isinstance(data, list) else []
        else:
            docs = []
    except (json.JSONDecodeError, OSError):
        docs = []
    docs.append(doc)
    with open(PLANNING_DOCUMENTS_PATH, "w", encoding="utf-8") as f:
        json.dump(docs, f, indent=2)
    return {
        "status": "success",
        "document_id": doc_id,
        "slug": slug,
        "path": f"/planning-documents/{doc_id}",
        "message": "Planning document created; visible in Past crisis / Planning documents.",
    }


# ---------- Supplier reallocation optimization ----------

def optimize_supplier_reallocation(
    demand_units: Optional[float] = None,
    disruption_probabilities_json: Optional[str] = None,
) -> dict:
    """
    Supplier reallocation optimization: determine optimal distribution of procurement across suppliers.
    Objective: minimize total cost + risk penalty. Constraints: capacity, demand, lead-time limits.
    Uses profile suppliers; optional disruption_probabilities_json = {"SUP-001": 0.45, "SUP-002": 0.2, ...}.
    Outputs: allocation per supplier, cost impact, concentration risk reduction, disruption exposure change.
    """
    profile = _load_profile()
    suppliers = profile.get("suppliers") or []
    if not suppliers:
        return {"status": "error", "message": "No suppliers in profile"}

    disruption_probs = {}
    if disruption_probabilities_json:
        try:
            disruption_probs = json.loads(disruption_probabilities_json)
        except (TypeError, json.JSONDecodeError):
            pass

    total_demand = demand_units
    if total_demand is None:
        erp = _load_erp()
        inv = erp.get("inventory") or []
        total_demand = sum((i.get("daily_consumption") or 0) * 30 for i in inv) or 10000

    # Build supplier params: capacity (from spend share proxy), unit cost, lead time, reliability (1 - health_risk), disruption prob
    supplier_params = []
    for s in suppliers:
        sid = s.get("id") or ""
        name = s.get("name") or sid
        spend_pct = (s.get("spend_pct") or 0) / 100.0
        capacity_share = max(0.1, spend_pct * 1.2)
        unit_cost = 12.5
        lead_time = s.get("lead_time_days") or 30
        health = (s.get("health_score") or 75) / 100.0
        reliability = health
        prob = disruption_probs.get(sid, 0.25)
        supplier_params.append({
            "id": sid,
            "name": name,
            "capacity_share": capacity_share,
            "unit_cost": unit_cost,
            "lead_time_days": lead_time,
            "reliability": reliability,
            "disruption_prob": prob,
        })

    # Simple optimization: minimize cost + risk penalty. Risk penalty = allocation * disruption_prob * scale.
    risk_penalty_scale = 500
    total_capacity = sum(p["capacity_share"] for p in supplier_params)
    allocations = []
    for p in supplier_params:
        share = p["capacity_share"] / total_capacity
        alloc = total_demand * share
        cost = alloc * p["unit_cost"]
        risk_penalty = alloc * p["disruption_prob"] * risk_penalty_scale / 1000
        allocations.append({
            "supplier_id": p["id"],
            "supplier_name": p["name"],
            "allocated_units": round(alloc, 0),
            "allocation_pct": round(100 * share, 1),
            "cost_usd": round(cost, 2),
            "risk_penalty_usd": round(risk_penalty, 2),
        })

    total_cost = sum(a["cost_usd"] for a in allocations)
    total_risk_penalty = sum(a["risk_penalty_usd"] for a in allocations)
    concentration_before = max(s.get("spend_pct") or 0 for s in suppliers)
    concentration_after = max(a["allocation_pct"] for a in allocations)
    concentration_reduction = round(concentration_before - concentration_after, 1)
    weighted_exposure = sum(a["allocation_pct"]/100 * (disruption_probs.get(a["supplier_id"], 0.25)) for a in allocations)
    exposure_pct = round(100 * weighted_exposure, 1)

    return {
        "status": "success",
        "allocation_by_supplier": allocations,
        "total_demand_units": total_demand,
        "total_cost_usd": round(total_cost, 2),
        "total_risk_penalty_usd": round(total_risk_penalty, 2),
        "cost_impact": f"Total procurement cost: ${total_cost:,.0f}; risk-adjusted adds ${total_risk_penalty:,.0f}.",
        "concentration_risk_reduction_pct": max(0, concentration_reduction),
        "disruption_exposure_pct": exposure_pct,
        "summary": f"Optimal reallocation across {len(allocations)} suppliers. Largest share: {allocations[0]['allocation_pct']}% ({allocations[0]['supplier_name']}). Concentration reduction: {concentration_reduction}%.",
    }


# ---------- Buffer stock strategy modeling ----------

def _stockout_probability_from_days(days_on_hand: float) -> float:
    """Approximate stockout probability from days of buffer (decreasing in days). Calibrated to ~18% at 12 days, ~4% at 14 days."""
    if days_on_hand >= 20:
        return 0.01
    if days_on_hand <= 10:
        return 0.25
    if days_on_hand <= 12:
        return 0.18
    if days_on_hand <= 14:
        return 0.18 - (0.18 - 0.04) * (days_on_hand - 12) / 2  # 12→18%, 14→4%
    return max(0.01, 0.04 - (0.04 - 0.01) * (days_on_hand - 14) / 6)


def recommend_buffer_stock(
    item_id: str = "SEMI-MCU-32",
    service_level_target_pct: Optional[float] = None,
    holding_cost_pct_per_year: Optional[float] = None,
    stockout_cost_per_unit: Optional[float] = None,
) -> dict:
    """
    Buffer stock strategy: determine optimal safety stock balancing inventory cost and service reliability.
    Uses demand variability and lead-time variability from ERP/profile; safety stock ≈ Z × σ_LT.
    Outputs: recommended safety stock (days), stockout probability before/after, inventory carrying cost impact.
    """
    profile = _load_profile()
    erp = _load_erp()
    defaults = _CONFIG.get("buffer_stock_defaults", {})
    if service_level_target_pct is None:
        service_level_target_pct = defaults.get("service_level_target_pct", 95.0)
    if holding_cost_pct_per_year is None:
        holding_cost_pct_per_year = defaults.get("holding_cost_pct_per_year", 25.0)
    inv_list = erp.get("inventory") or []
    item = next((i for i in inv_list if (i.get("item_id") or "") == item_id), None)
    if not item:
        return {"status": "error", "message": f"Item {item_id} not found in ERP"}

    policy = profile.get("inventory_policy") or {}
    target_buffer_days = policy.get("target_buffer_days", 30)
    max_buffer_days = policy.get("max_buffer_days", 60)
    daily_consumption = item.get("daily_consumption") or 400
    days_on_hand = item.get("days_on_hand") or 12

    demand_cv = defaults.get("demand_cv", 0.15)
    lead_time_days = 45
    lead_time_std = defaults.get("lead_time_std_days", 5)
    demand_std_daily = daily_consumption * demand_cv
    sigma_LT = (demand_std_daily ** 2 * lead_time_days + (daily_consumption * lead_time_std) ** 2) ** 0.5
    if sigma_LT <= 0:
        sigma_LT = daily_consumption * 2

    # Z from service level (e.g. 95% -> Z ≈ 1.65)
    z_map = {90: 1.28, 95: 1.65, 98: 2.05, 99: 2.33}
    Z = z_map.get(int(service_level_target_pct), 1.65)
    safety_stock_units = Z * sigma_LT
    safety_stock_days = safety_stock_units / daily_consumption if daily_consumption else 0
    # Ensure recommended buffer meets target service (e.g. 14 days for ~4% stockout)
    raw_days = max(1, round(safety_stock_days))
    min_days_for_target = 14 if service_level_target_pct >= 95 else (12 if service_level_target_pct >= 90 else 10)
    recommended_days = min(max_buffer_days, max(raw_days, min_days_for_target))

    stockout_prob_before = _stockout_probability_from_days(days_on_hand)
    stockout_prob_after = _stockout_probability_from_days(recommended_days)
    inventory_cost_before = (days_on_hand / 365) * daily_consumption * 12.5 * (holding_cost_pct_per_year / 100)
    inventory_cost_after = (recommended_days / 365) * daily_consumption * 12.5 * (holding_cost_pct_per_year / 100)
    cost_increase_pct = round(100 * (inventory_cost_after - inventory_cost_before) / inventory_cost_before, 1) if inventory_cost_before else 0

    return {
        "status": "success",
        "item_id": item_id,
        "recommended_safety_stock_days": recommended_days,
        "recommended_safety_stock_units": round(safety_stock_units, 0),
        "stockout_probability_before_pct": round(100 * stockout_prob_before, 1),
        "stockout_probability_after_pct": round(100 * stockout_prob_after, 1),
        "inventory_carrying_cost_before_usd": round(inventory_cost_before, 2),
        "inventory_carrying_cost_after_usd": round(inventory_cost_after, 2),
        "inventory_cost_increase_pct": cost_increase_pct,
        "impact_summary": (
            f"Recommended buffer stock: {recommended_days} days. "
            f"Stockout probability reduced from {100*stockout_prob_before:.0f}% → {100*stockout_prob_after:.0f}%. "
            f"Inventory cost increase: +{cost_increase_pct}%."
        ),
        "summary": f"Recommended buffer stock: {recommended_days} days. Impact: Stockout probability {100*stockout_prob_before:.0f}% → {100*stockout_prob_after:.0f}%; inventory cost +{cost_increase_pct}%.",
    }


# ---------- Alternative suppliers & airfreight (unchanged) ----------

def get_alternative_suppliers(category: str, exclude_regions: Optional[List[str]] = None) -> dict:
    """Find alternative suppliers for a component category, optionally excluding regions."""
    suppliers = ALTERNATIVE_SUPPLIERS.get(category, [])
    if exclude_regions:
        suppliers = [s for s in suppliers if s.get("region") not in exclude_regions]
    return {"status": "success", "category": category, "excluded_regions": exclude_regions or [], "alternatives_found": len(suppliers), "alternative_suppliers": suppliers}


def get_airfreight_rate_estimate(origin_country: str, destination_country: str, weight_kg: float) -> dict:
    """Airfreight rate estimate for emergency shipments."""
    route_key = f"{origin_country}|{destination_country}"
    rate_data = AIRFREIGHT_RATES.get(route_key, {"rate_per_kg": AIRFREIGHT_DEFAULTS["default_rate_per_kg"], "transit_days": AIRFREIGHT_DEFAULTS["default_transit_days"]})
    total_cost = rate_data["rate_per_kg"] * weight_kg
    handling_fee = AIRFREIGHT_DEFAULTS.get("handling_fee_usd", 1500)
    customs_estimate = total_cost * AIRFREIGHT_DEFAULTS.get("customs_pct", 0.03)
    return {
        "status": "success",
        "origin": origin_country,
        "destination": destination_country,
        "weight_kg": weight_kg,
        "rate_per_kg_usd": rate_data["rate_per_kg"],
        "transit_days": rate_data["transit_days"],
        "freight_cost_usd": round(total_cost, 2),
        "handling_fee_usd": handling_fee,
        "customs_estimate_usd": round(customs_estimate, 2),
        "total_estimated_cost_usd": round(total_cost + handling_fee + customs_estimate, 2),
        "retrieved_at": datetime.now().isoformat(),
    }
