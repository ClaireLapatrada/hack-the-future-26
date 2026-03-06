"""
Typed return models for every tool function in tools/*.py.

These mirror the dict shapes returned today; no business logic changes.
Tools can adopt these incrementally by returning ModelName(**result) instead
of a bare dict — the wire format is identical.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from backend.models.active_disruption import ShippingLaneStatus


# ── Perception Tools ──────────────────────────────────────────────────────────

class NewsSignal(BaseModel):
    title: str
    source: str
    published: str
    url: str
    summary: str
    classified_type: Optional[str] = None
    severity: Optional[str] = None
    confidence_score: Optional[float] = None


class DisruptionNewsResult(BaseModel):
    status: str
    query: str
    articles_found: int
    signals: List[NewsSignal] = []
    scan_timestamp: str
    message: Optional[str] = None


class ShippingLaneStatusResult(BaseModel):
    status: str
    lane: str
    lane_status: ShippingLaneStatus
    message: Optional[str] = None


class ClimateAlert(BaseModel):
    type: str
    name: str
    severity: str
    affected_area: str
    expected_impact_days: Optional[int] = None
    logistics_disruption_risk: str
    eonet_id: Optional[str] = None
    source: str


class RegionAlerts(BaseModel):
    active_alerts: List[ClimateAlert] = []


class ClimateAlertsResult(BaseModel):
    status: str
    regions_checked: List[str]
    alerts: Dict[str, RegionAlerts]
    scan_timestamp: str
    message: Optional[str] = None


class SupplierHealthData(BaseModel):
    supplier_name: str
    overall_health_score: Optional[float] = None
    financial_stability: Optional[str] = None
    payment_behavior: Optional[str] = None
    operational_reliability: Optional[str] = None
    geopolitical_risk_exposure: Optional[str] = None
    recent_flags: List[str] = []
    trend: Optional[str] = None
    recommendation: Optional[str] = None


class SupplierHealthResult(BaseModel):
    status: str
    supplier_id: str
    health_data: SupplierHealthData
    message: Optional[str] = None


# ── Risk Tools ────────────────────────────────────────────────────────────────

class AtRiskProductionLine(BaseModel):
    line_id: str
    product: str
    days_on_hand: float
    stockout_day: float
    production_halt_days: float
    daily_revenue_usd: float
    revenue_at_risk_usd: float


class RevenueAtRiskResult(BaseModel):
    status: str
    supplier_id: Optional[str] = None
    disruption_duration_days: Optional[int] = None
    affected_production_lines: List[AtRiskProductionLine] = []
    total_revenue_at_risk_usd: float = 0.0
    sla_penalties_at_risk_usd: float = 0.0
    total_financial_exposure_usd: float = 0.0
    summary: str = ""
    message: Optional[str] = None


class InventoryRunwayResult(BaseModel):
    status: str
    item_id: Optional[str] = None
    description: Optional[str] = None
    supplier_id: Optional[str] = None
    days_on_hand: Optional[float] = None
    daily_consumption: Optional[float] = None
    stock_units: Optional[int] = None
    on_order_units: Optional[int] = None
    expected_delivery_date: Optional[str] = None
    reorder_threshold_days: Optional[int] = None
    target_buffer_days: Optional[int] = None
    alert_level: Optional[str] = None
    days_until_stockout: Optional[float] = None
    summary: Optional[str] = None
    message: Optional[str] = None


class SlaBreachResult(BaseModel):
    status: str
    customer: Optional[str] = None
    sla_target_pct: Optional[float] = None
    production_halt_days: Optional[float] = None
    breach_probability: Optional[float] = None
    breach_probability_pct: Optional[str] = None
    penalty_per_day_usd: Optional[float] = None
    total_penalty_exposure_usd: Optional[float] = None
    severity: Optional[str] = None
    message: Optional[str] = None


class SupplierExposureResult(BaseModel):
    status: str
    supplier: Optional[Dict[str, Any]] = None
    open_purchase_orders: List[Dict[str, Any]] = []
    total_open_po_value_usd: Optional[float] = None
    risk_flags: List[str] = []
    overall_risk_rating: Optional[str] = None
    summary: Optional[str] = None
    message: Optional[str] = None


class RiskIndicators(BaseModel):
    supplier_delivery_delay_frequency: float
    supplier_financial_health_score: float
    region_instability_index: float
    logistics_congestion_score: float
    weather_disruption_probability: float


class DisruptionProbabilityResult(BaseModel):
    status: str
    supplier_id: Optional[str] = None
    supplier_name: Optional[str] = None
    time_horizon_days: Optional[int] = None
    disruption_probability_pct: Optional[float] = None
    risk_classification: Optional[str] = None
    primary_drivers: List[str] = []
    risk_indicators: Optional[RiskIndicators] = None
    summary: Optional[str] = None
    message: Optional[str] = None


class RevenueAtRiskScenario(BaseModel):
    revenue_at_risk_usd: float
    sla_penalties_usd: float
    margin_impact_usd: float
    delay_days: int


class RevenueAtRiskExecutiveResult(BaseModel):
    status: str
    revenue_at_risk_usd: Optional[float] = None
    margin_impact_usd: Optional[float] = None
    sla_penalties_usd: Optional[float] = None
    customers_affected: Optional[int] = None
    best_case: Optional[RevenueAtRiskScenario] = None
    expected_case: Optional[RevenueAtRiskScenario] = None
    worst_case: Optional[RevenueAtRiskScenario] = None
    summary: Optional[str] = None
    message: Optional[str] = None


# ── Operational Impact Tools ──────────────────────────────────────────────────

class AffectedProductionLine(BaseModel):
    line_id: str
    product: str
    daily_revenue_usd: float
    at_risk: bool


class CriticalDependency(BaseModel):
    item_id: str
    supplier_id: Optional[str] = None
    single_source: bool
    line_id: str


class OperationalImpactResult(BaseModel):
    status: str
    production_downtime_probability_pct: Optional[float] = None
    affected_production_lines: List[AffectedProductionLine] = []
    estimated_delay_days_min: Optional[int] = None
    estimated_delay_days_max: Optional[int] = None
    critical_component_dependencies: List[CriticalDependency] = []
    summary: Optional[str] = None
    message: Optional[str] = None


# ── Planning Tools ────────────────────────────────────────────────────────────

class ScenarioTableEntry(BaseModel):
    scenario_id: str
    scenario_name: str
    expected_cost_increase_usd: float
    expected_service_level: str
    average_score: float
    description: str


class ScenarioSimulationResult(BaseModel):
    status: str
    scenario_comparison_table: List[ScenarioTableEntry] = []
    recommended_scenario: Optional[str] = None
    recommended_scenario_id: Optional[str] = None
    expected_service_level_performance: Optional[str] = None
    expected_cost_increase_usd: Optional[float] = None
    expected_cost_increase_pct: Optional[float] = None
    disruption_resilience_improvement: Optional[str] = None
    monte_carlo_runs: Optional[int] = None
    risk_appetite: Optional[str] = None
    summary: Optional[str] = None
    message: Optional[str] = None


class RankScenariosResult(BaseModel):
    status: str
    risk_appetite: Optional[str] = None
    ranked_scenarios: List[Dict[str, Any]] = []
    top_recommendation: Optional[str] = None
    reasoning: Optional[str] = None
    message: Optional[str] = None


class TradeoffScenario(BaseModel):
    name: str
    cost_usd: float
    service_level: str
    resilience_note: str
    adjusted_score: Optional[float] = None


class MitigationTradeoffsResult(BaseModel):
    status: str
    recommended_strategy: Optional[str] = None
    scenarios: List[TradeoffScenario] = []
    cost_vs_resilience: List[str] = []
    service_level_impact: Optional[str] = None
    summary: Optional[str] = None
    message: Optional[str] = None


class CreatePlanningDocumentResult(BaseModel):
    status: str
    document_id: Optional[str] = None
    slug: Optional[str] = None
    path: Optional[str] = None
    message: Optional[str] = None


class SupplierAllocation(BaseModel):
    supplier_id: str
    supplier_name: str
    allocated_units: float
    allocation_pct: float
    cost_usd: float
    risk_penalty_usd: float


class SupplierReallocationResult(BaseModel):
    status: str
    allocation_by_supplier: List[SupplierAllocation] = []
    total_demand_units: Optional[float] = None
    total_cost_usd: Optional[float] = None
    total_risk_penalty_usd: Optional[float] = None
    cost_impact: Optional[str] = None
    concentration_risk_reduction_pct: Optional[float] = None
    disruption_exposure_pct: Optional[float] = None
    summary: Optional[str] = None
    message: Optional[str] = None


class BufferStockResult(BaseModel):
    status: str
    item_id: Optional[str] = None
    recommended_safety_stock_days: Optional[int] = None
    recommended_safety_stock_units: Optional[float] = None
    stockout_probability_before_pct: Optional[float] = None
    stockout_probability_after_pct: Optional[float] = None
    inventory_carrying_cost_before_usd: Optional[float] = None
    inventory_carrying_cost_after_usd: Optional[float] = None
    inventory_cost_increase_pct: Optional[float] = None
    impact_summary: Optional[str] = None
    summary: Optional[str] = None
    message: Optional[str] = None


class AlternativeSuppliersResult(BaseModel):
    status: str
    category: str
    excluded_regions: List[str] = []
    alternatives_found: int
    alternative_suppliers: List[Dict[str, Any]] = []


class AirfreightRateResult(BaseModel):
    status: str
    origin: str
    destination: str
    weight_kg: float
    rate_per_kg_usd: float
    transit_days: int
    freight_cost_usd: float
    handling_fee_usd: float
    customs_estimate_usd: float
    total_estimated_cost_usd: float
    retrieved_at: str


# ── Action Tools ──────────────────────────────────────────────────────────────

class DraftEmail(BaseModel):
    to: str
    subject: str
    body: str
    priority: str
    draft_timestamp: str


class DraftEmailResult(BaseModel):
    status: str
    draft_email: Optional[DraftEmail] = None
    next_step: Optional[str] = None
    auto_send_eligible: Optional[bool] = None
    reference_id: Optional[str] = None
    message: Optional[str] = None


class SlackAlertResult(BaseModel):
    status: str
    channel: Optional[str] = None
    severity: Optional[str] = None
    message_preview: Optional[str] = None
    blocks: List[Dict[str, Any]] = []
    sent_at: Optional[str] = None
    mock_note: Optional[str] = None
    message: Optional[str] = None


class ErpChangeRecord(BaseModel):
    change_id: str
    item_id: str
    adjustment_type: str
    description: str
    quantity: int
    reason: str
    status: str
    created_at: str
    created_by: str
    approval_required: bool


class ErpReorderResult(BaseModel):
    status: str
    erp_change: Optional[ErpChangeRecord] = None
    next_step: Optional[str] = None
    mock_note: Optional[str] = None
    message: Optional[str] = None


class PoSuggestion(BaseModel):
    item_id: str
    description: str
    suggested_quantity: int
    reason: str
    estimated_cost_usd: float
    auto_eligible: bool
    days_on_hand: float
    target_buffer_days: int


class PoAdjustmentResult(BaseModel):
    status: str
    suggestions: List[PoSuggestion] = []
    auto_restock_threshold_usd: Optional[float] = None
    summary: Optional[str] = None
    message: Optional[str] = None


class SubmitRestockResult(BaseModel):
    status: str
    approval_id: Optional[str] = None
    message: Optional[str] = None
    next_step: Optional[str] = None


class ExecuteRestockResult(BaseModel):
    status: str
    approval_id: Optional[str] = None
    erp_result: Optional[Dict[str, Any]] = None
    message: Optional[str] = None


class EscalateResult(BaseModel):
    status: str
    escalation_id: Optional[str] = None
    trigger_reason: Optional[str] = None
    suggested_recipients: Optional[str] = None
    message: Optional[str] = None


class ClientContextResult(BaseModel):
    status: str
    client_context: Dict[str, Any] = {}
    summary: Optional[str] = None


class WorkflowIntegrationResult(BaseModel):
    status: str
    integrations: Dict[str, Any] = {}
    connected_systems: List[str] = []
    one_stop_ui_summary: Optional[str] = None


class SubmitMitigationResult(BaseModel):
    status: str
    approval_id: Optional[str] = None
    message: Optional[str] = None
    next_step: Optional[str] = None


class ExecutiveSummaryResult(BaseModel):
    status: str
    summary: Optional[str] = None
    generated_at: Optional[str] = None
    severity: Optional[str] = None
    financial_exposure_usd: Optional[float] = None
    decision_deadline_hours: Optional[int] = None
    message: Optional[str] = None


# ── Memory Tools ──────────────────────────────────────────────────────────────

class SimilarCase(BaseModel):
    event_id: Optional[str] = None
    date: Optional[str] = None
    type: Optional[str] = None
    description: Optional[str] = None
    what_worked: Optional[str] = None
    outcome: Optional[str] = None
    cost_usd: Optional[float] = None
    actual_loss_usd: Optional[float] = None
    lesson: Optional[str] = None


class SimilarDisruptionsResult(BaseModel):
    status: str
    query: Dict[str, str] = {}
    similar_cases_found: int = 0
    cases: List[SimilarCase] = []
    summary: str = ""
    source: Optional[str] = None


class LogEventResult(BaseModel):
    status: str
    event_id: Optional[str] = None
    logged_event: Optional[Dict[str, Any]] = None
    storage_status: Optional[str] = None
    note: Optional[str] = None
    message: Optional[str] = None


class RecurringPattern(BaseModel):
    pattern: str
    detail: str
    recommendation: str


class RecurringPatternsResult(BaseModel):
    status: str
    total_events_analyzed: int = 0
    total_historical_losses_usd: float = 0.0
    total_mitigation_costs_usd: float = 0.0
    disruption_by_type: Dict[str, int] = {}
    disruption_by_region: Dict[str, int] = {}
    most_affected_suppliers: Dict[str, int] = {}
    recurring_patterns: List[RecurringPattern] = []
    summary: str = ""
    message: Optional[str] = None
