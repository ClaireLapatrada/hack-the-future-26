"""Pydantic model registry — import all domain models for convenient access."""
from backend.models.stream import StreamEntry, StreamEntryType
from backend.models.disruptions import (
    DisruptionEvent,
    DisruptionImpact,
    DisruptionListItem,
    DisruptionSeverity,
    MitigationTaken,
    TimelineEntry,
)
from backend.models.active_disruption import ActiveDisruptionConfig, ShippingLaneStatus
from backend.models.approvals import ApprovalEntry, ApprovalStatus, AuditLogEntry, EscalationRecord
from backend.models.planning import (
    PlanningDocument,
    RankedScenario,
    ScenarioComparison,
    ScenarioFinancials,
    ScenarioResult,
    ScenarioTiming,
)
from backend.models.erp import ErpSnapshot, InventoryItem, PurchaseOrder
from backend.models.profile import (
    CustomerSLA,
    InventoryPolicy,
    ManufacturerProfile,
    ProductionLine,
    Supplier,
)
from backend.models.rules import InputRule, RuleDef, RuleSection, RulesConfig, SliderRule, ToggleRule
from backend.models.tool_results import (
    AffectedProductionLine,
    AirfreightRateResult,
    AlternativeSuppliersResult,
    AtRiskProductionLine,
    BufferStockResult,
    ClimateAlertsResult,
    ClientContextResult,
    CreatePlanningDocumentResult,
    CriticalDependency,
    DisruptionNewsResult,
    DisruptionProbabilityResult,
    DraftEmailResult,
    ErpReorderResult,
    EscalateResult,
    ExecuteRestockResult,
    ExecutiveSummaryResult,
    InventoryRunwayResult,
    LogEventResult,
    MitigationTradeoffsResult,
    NewsSignal,
    OperationalImpactResult,
    PoAdjustmentResult,
    RankScenariosResult,
    RecurringPatternsResult,
    RevenueAtRiskExecutiveResult,
    RevenueAtRiskResult,
    ScenarioSimulationResult,
    ShippingLaneStatusResult,
    SlaBreachResult,
    SlackAlertResult,
    SimilarDisruptionsResult,
    SubmitMitigationResult,
    SubmitRestockResult,
    SupplierExposureResult,
    SupplierHealthResult,
    SupplierReallocationResult,
    WorkflowIntegrationResult,
)

__all__ = [
    # stream
    "StreamEntry", "StreamEntryType",
    # disruptions
    "DisruptionEvent", "DisruptionImpact", "DisruptionListItem",
    "DisruptionSeverity", "MitigationTaken", "TimelineEntry",
    # active disruption
    "ActiveDisruptionConfig", "ShippingLaneStatus",
    # approvals
    "ApprovalEntry", "ApprovalStatus", "AuditLogEntry", "EscalationRecord",
    # planning
    "PlanningDocument", "RankedScenario", "ScenarioComparison",
    "ScenarioFinancials", "ScenarioResult", "ScenarioTiming",
    # erp
    "ErpSnapshot", "InventoryItem", "PurchaseOrder",
    # profile
    "CustomerSLA", "InventoryPolicy", "ManufacturerProfile", "ProductionLine", "Supplier",
    # rules
    "InputRule", "RuleDef", "RuleSection", "RulesConfig", "SliderRule", "ToggleRule",
    # tool results
    "AffectedProductionLine", "AirfreightRateResult", "AlternativeSuppliersResult",
    "AtRiskProductionLine", "BufferStockResult", "ClimateAlertsResult",
    "ClientContextResult", "CreatePlanningDocumentResult", "CriticalDependency",
    "DisruptionNewsResult", "DisruptionProbabilityResult", "DraftEmailResult",
    "ErpReorderResult", "EscalateResult", "ExecuteRestockResult",
    "ExecutiveSummaryResult", "InventoryRunwayResult", "LogEventResult",
    "MitigationTradeoffsResult", "NewsSignal", "OperationalImpactResult",
    "PoAdjustmentResult", "RankScenariosResult", "RecurringPatternsResult",
    "RevenueAtRiskExecutiveResult", "RevenueAtRiskResult", "ScenarioSimulationResult",
    "ShippingLaneStatusResult", "SlaBreachResult", "SlackAlertResult",
    "SimilarDisruptionsResult", "SubmitMitigationResult", "SubmitRestockResult",
    "SupplierExposureResult", "SupplierHealthResult", "SupplierReallocationResult",
    "WorkflowIntegrationResult",
]
