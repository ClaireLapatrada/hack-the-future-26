"""
Planning Tools — Scenario simulation and mitigation strategy generation.
Used by the Scenario Planning Agent.
Config and static data are loaded from planning_config.json (project root).
"""

import json
from pathlib import Path
from datetime import datetime

# Load config once at import (project root = parent of tools/)
_CONFIG_PATH = Path(__file__).resolve().parent.parent / "planning_config.json"
with open(_CONFIG_PATH, encoding="utf-8") as _f:
    _CONFIG = json.load(_f)

SCENARIOS = _CONFIG["scenario_definitions"]
ALTERNATIVE_SUPPLIERS = _CONFIG["alternative_suppliers"]
AIRFREIGHT_RATES = _CONFIG["airfreight_rates"]
AIRFREIGHT_DEFAULTS = _CONFIG["airfreight_defaults"]
RISK_WEIGHTS = _CONFIG["risk_appetite_weights"]
SERVICE_LEVEL_SCORES = _CONFIG["service_level_scores"]
RANK_SERVICE_SCORES = _CONFIG["rank_service_scores"]


def simulate_mitigation_scenario(
    scenario_type: str,
    affected_item_id: str,
    disruption_days: int,
    quantity_needed: int
) -> dict:
    """
    Simulate a specific mitigation scenario and return cost, time, and risk trade-offs.

    Args:
        scenario_type: One of "airfreight", "alternate_supplier", "buffer_build",
                       "demand_deferral", "spot_market"
        affected_item_id: ERP item ID e.g. "SEMI-MCU-32"
        disruption_days: Expected disruption duration in days
        quantity_needed: Units needed to cover production gap
    """
    scenario = SCENARIOS.get(scenario_type)
    if not scenario:
        return {"status": "error", "message": f"Unknown scenario type: {scenario_type}"}

    # Cost calculation
    premium_unit_cost = scenario["base_unit_cost_usd"] * (1 + scenario["unit_cost_premium_pct"] / 100)
    variable_cost = premium_unit_cost * quantity_needed
    total_cost = variable_cost + scenario["fixed_cost_usd"]
    baseline_cost = scenario["base_unit_cost_usd"] * quantity_needed
    incremental_cost = total_cost - baseline_cost

    # Score (0-100): balance of cost, speed, service level
    service_score = SERVICE_LEVEL_SCORES.get(scenario["service_level_protection"], 50)
    cost_score = max(0, 100 - (scenario["unit_cost_premium_pct"] / 3))
    speed_score = max(0, 100 - (scenario["implementation_days"] * 4))
    composite_score = (service_score * 0.5 + cost_score * 0.3 + speed_score * 0.2)

    return {
        "status": "success",
        "scenario_type": scenario_type,
        "scenario_name": scenario["name"],
        "description": scenario["description"],
        "financials": {
            "incremental_cost_usd": round(incremental_cost, 2),
            "total_cost_usd": round(total_cost, 2),
            "unit_cost_premium_pct": scenario["unit_cost_premium_pct"]
        },
        "timing": {
            "implementation_days": scenario["implementation_days"],
            "lead_time_change_days": scenario["lead_time_reduction_days"]
        },
        "service_level_protection": scenario["service_level_protection"],
        "risks": scenario["risks"],
        "composite_score": round(composite_score, 1),
        "co2_impact": scenario["co2_impact"]
    }


def get_alternative_suppliers(
    category: str,
    exclude_regions: list[str] | None = None
) -> dict:
    """
    Find alternative suppliers for a given component category,
    optionally excluding certain risk regions.

    Args:
        category: Component category e.g. "Semiconductors", "Plastic Injection Parts"
        exclude_regions: Regions to exclude e.g. ["Taiwan", "Vietnam"]
    """
    suppliers = ALTERNATIVE_SUPPLIERS.get(category, [])

    if exclude_regions:
        suppliers = [s for s in suppliers if s["region"] not in exclude_regions]

    return {
        "status": "success",
        "category": category,
        "excluded_regions": exclude_regions or [],
        "alternatives_found": len(suppliers),
        "alternative_suppliers": suppliers
    }


def get_airfreight_rate_estimate(
    origin_country: str,
    destination_country: str,
    weight_kg: float
) -> dict:
    """
    Get airfreight rate estimate for emergency shipments.
    In production: wraps Freightos or Xeneta API.

    Args:
        origin_country: Country of origin e.g. "Taiwan"
        destination_country: Country of destination e.g. "Germany"
        weight_kg: Shipment weight in kilograms
    """
    route_key = f"{origin_country}|{destination_country}"
    rate_data = AIRFREIGHT_RATES.get(
        route_key,
        {"rate_per_kg": AIRFREIGHT_DEFAULTS["default_rate_per_kg"], "transit_days": AIRFREIGHT_DEFAULTS["default_transit_days"]}
    )

    total_cost = rate_data["rate_per_kg"] * weight_kg
    handling_fee = AIRFREIGHT_DEFAULTS["handling_fee_usd"]
    customs_estimate = total_cost * AIRFREIGHT_DEFAULTS["customs_pct"]

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
        "retrieved_at": datetime.now().isoformat()
    }


def rank_scenarios(scenarios_json: str, risk_appetite: str = "low") -> dict:
    """
    Rank mitigation scenarios by composite score adjusted for company risk appetite.

    Args:
        scenarios_json: JSON array of scenario objects from simulate_mitigation_scenario, e.g. [{"scenario_type": "airfreight", "financials": {...}, "timing": {...}, "service_level_protection": "High"}, ...]
        risk_appetite: "low", "medium", or "high"
    """
    try:
        scenarios = json.loads(scenarios_json)
    except (TypeError, json.JSONDecodeError):
        return {"status": "error", "message": "scenarios_json must be a valid JSON array of scenario objects"}
    if not isinstance(scenarios, list):
        return {"status": "error", "message": "scenarios_json must be a JSON array"}
    w = RISK_WEIGHTS.get(risk_appetite, RISK_WEIGHTS["low"])

    ranked = []
    for s in scenarios:
        service_score = RANK_SERVICE_SCORES.get(
            s.get("service_level_protection", "Low"), 20)
        cost_score = max(0, 100 - s.get("financials", {}).get("unit_cost_premium_pct", 0) / 3)
        speed_score = max(0, 100 - s.get("timing", {}).get("implementation_days", 30) * 3)
        adjusted_score = (
            service_score * w["service"] +
            cost_score * w["cost"] +
            speed_score * w["speed"]
        )
        ranked.append({**s, "adjusted_score": round(adjusted_score, 1)})

    ranked.sort(key=lambda x: x["adjusted_score"], reverse=True)

    return {
        "status": "success",
        "risk_appetite": risk_appetite,
        "ranked_scenarios": ranked,
        "top_recommendation": ranked[0]["scenario_name"] if ranked else None,
        "reasoning": f"Based on '{risk_appetite}' risk appetite, "
                     f"service level protection is weighted at {w['service']*100:.0f}%. "
                     f"'{ranked[0]['scenario_name']}' scores highest at {ranked[0]['adjusted_score']:.1f}/100."
                     if ranked else "No scenarios to rank."
    }