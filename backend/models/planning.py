"""Pydantic models for planning documents and scenario simulation."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class ScenarioComparison(BaseModel):
    scenario_id: Optional[str] = None
    scenario_name: Optional[str] = None
    expected_cost_increase_usd: Optional[float] = None
    expected_service_level: Optional[str] = None
    average_score: Optional[float] = None
    description: Optional[str] = None


class PlanningDocument(BaseModel):
    id: str
    slug: str
    title: str
    createdAt: str
    situationSummary: str
    recommendedScenario: str
    scenarioComparison: List[ScenarioComparison] = []
    costImpactSummary: str
    serviceLevelImpact: str
    documentType: str
    affectedItemId: Optional[str] = None
    riskAppetite: Optional[str] = None


class ScenarioFinancials(BaseModel):
    incremental_cost_usd: float
    total_cost_usd: float
    unit_cost_premium_pct: float


class ScenarioTiming(BaseModel):
    implementation_days: int
    lead_time_change_days: int


class ScenarioResult(BaseModel):
    """Return type of simulate_mitigation_scenario."""
    status: str
    scenario_type: str
    scenario_name: str
    description: str
    financials: ScenarioFinancials
    timing: ScenarioTiming
    service_level_protection: str
    risks: List[str] = []
    composite_score: float
    co2_impact: Optional[str] = None


class RankedScenario(BaseModel):
    """A scenario with an appended adjusted_score from rank_scenarios."""
    scenario_type: Optional[str] = None
    scenario_name: Optional[str] = None
    description: Optional[str] = None
    financials: Optional[ScenarioFinancials] = None
    timing: Optional[ScenarioTiming] = None
    service_level_protection: Optional[str] = None
    composite_score: Optional[float] = None
    adjusted_score: Optional[float] = None
    risks: Optional[List[str]] = None
    co2_impact: Optional[str] = None
