"""
POST /api/scenarios/run

Runs scenario simulation and ranking using the Python planning tools.
Replaces the duplicated logic in ui/app/api/scenarios/run/route.ts.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel

router = APIRouter()


class ScenarioRunRequest(BaseModel):
    eventId: Optional[str] = None
    event_id: Optional[str] = None
    bufferDays: int = 14
    riskAppetite: Literal["low", "medium", "high"] = "low"


class RankedScenarioItem(BaseModel):
    scenarioType: str
    scenarioName: str
    description: Optional[str] = None
    incrementalCostUsd: Optional[float] = None
    implementationDays: Optional[int] = None
    serviceLevelProtection: Optional[str] = None
    adjustedScore: Optional[float] = None


class TopRecommendation(BaseModel):
    scenarioName: str
    incrementalCostUsd: Optional[float] = None
    implementationDays: Optional[int] = None
    serviceLevelProtection: Optional[str] = None


class ScenarioRunResponse(BaseModel):
    eventId: Optional[str] = None
    bufferDays: int
    riskAppetite: str
    affectedItemId: str
    disruptionDays: int
    quantityNeeded: int
    rankedScenarios: List[RankedScenarioItem]
    topRecommendation: Optional[TopRecommendation] = None


@router.post("/api/scenarios/run", response_model=ScenarioRunResponse)
def run_scenarios(body: ScenarioRunRequest = Body(...)) -> Dict[str, Any]:
    """
    Simulate and rank mitigation scenarios.

    Calls simulate_mitigation_scenario and rank_scenarios from planning_tools
    directly, matching the logic the TS route was duplicating.
    """
    from backend.tools.planning_tools import simulate_mitigation_scenario, rank_scenarios
    from backend.settings import settings

    event_id = body.eventId or body.event_id
    buffer_days = body.bufferDays
    risk_appetite = body.riskAppetite

    import json
    disruption_days = 10
    affected_item_id = None
    quantity_needed = 4000

    if event_id:
        # Try to get disruption details from history
        history_path = settings.data_dir / "mock_disruption_history.json"
        if history_path.exists():
            try:
                events = json.loads(history_path.read_text(encoding="utf-8"))
                event = next((e for e in events if e.get("event_id") == event_id), None)
                if event and event.get("impact", {}).get("delay_days") is not None:
                    disruption_days = int(event["impact"]["delay_days"])
            except Exception:
                pass

    # Pick first critical item with daily consumption from ERP
    erp_path = settings.effective_erp_path
    if erp_path.exists():
        try:
            erp = json.loads(erp_path.read_text(encoding="utf-8"))
            inventory = erp.get("inventory") or []
            item = next(
                (i for i in inventory if i.get("daily_consumption") and i["daily_consumption"] > 0),
                None,
            )
            if item:
                affected_item_id = item["item_id"]
                quantity_needed = max(
                    1000,
                    int(disruption_days * item["daily_consumption"] * 0.8 + 0.5),
                )
        except Exception:
            pass

    if not affected_item_id:
        affected_item_id = "UNKNOWN-ITEM"

    scenario_types = ["airfreight", "buffer_build", "alternate_supplier"]
    simulated = []
    for scenario_type in scenario_types:
        try:
            result = simulate_mitigation_scenario(
                scenario_type=scenario_type,
                quantity_needed=quantity_needed,
                affected_item_id=affected_item_id,
            )
            if result.get("status") == "success":
                simulated.append(result)
        except Exception:
            pass

    ranked: List[Dict[str, Any]] = []
    if simulated:
        try:
            rank_result = rank_scenarios(
                scenarios=simulated,
                risk_appetite=risk_appetite,
            )
            ranked = rank_result.get("ranked_scenarios") or simulated
        except Exception:
            ranked = simulated

    ranked_items = [
        RankedScenarioItem(
            scenarioType=s.get("scenario_type", ""),
            scenarioName=s.get("scenario_name", ""),
            description=s.get("description"),
            incrementalCostUsd=s.get("financials", {}).get("incremental_cost_usd"),
            implementationDays=s.get("timing", {}).get("implementation_days"),
            serviceLevelProtection=s.get("service_level_protection"),
            adjustedScore=s.get("adjusted_score"),
        )
        for s in ranked
    ]

    top = ranked_items[0] if ranked_items else None
    top_rec = (
        TopRecommendation(
            scenarioName=top.scenarioName,
            incrementalCostUsd=top.incrementalCostUsd,
            implementationDays=top.implementationDays,
            serviceLevelProtection=top.serviceLevelProtection,
        )
        if top
        else None
    )

    return ScenarioRunResponse(
        eventId=event_id,
        bufferDays=buffer_days,
        riskAppetite=risk_appetite,
        affectedItemId=affected_item_id,
        disruptionDays=disruption_days,
        quantityNeeded=quantity_needed,
        rankedScenarios=ranked_items,
        topRecommendation=top_rec,
    ).model_dump()
