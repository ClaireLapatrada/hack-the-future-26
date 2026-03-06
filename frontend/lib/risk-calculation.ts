/**
 * Risk Intelligence Engine — same disruption probability model as tools/risk_tools.py.
 * Used by the dashboard API to show disruption probability (0–100%), classification, and primary drivers.
 */

export type SupplierProfile = {
  id: string;
  name: string;
  country?: string;
  spend_pct?: number;
  lead_time_days?: number;
  single_source?: boolean;
  health_score?: number;
  [k: string]: unknown;
};

export type DisruptionEvent = {
  event_id?: string;
  date?: string;
  type?: string;
  region?: string;
  severity?: string;
  affected_suppliers?: string[];
  description?: string;
  impact?: {
    delay_days?: number | null;
    revenue_at_risk_usd?: number | null;
    actual_revenue_lost_usd?: number | null;
  };
  [k: string]: unknown;
};

export type ActiveDisruptionConfig = {
  active?: boolean;
  supplier_health_degraded?: boolean;
  shipping_lanes?: Record<string, { status?: string; severity?: string; [k: string]: unknown }>;
};

export type SupplierRiskResult = {
  supplier_id: string;
  supplier_name: string;
  time_horizon_days: number;
  disruption_probability_pct: number;
  risk_classification: "Low" | "Medium" | "High";
  primary_drivers: string[];
  risk_indicators: {
    supplier_delivery_delay_frequency: number;
    supplier_financial_health_score: number;
    region_instability_index: number;
    logistics_congestion_score: number;
    weather_disruption_probability: number;
  };
};

const TIME_HORIZON_DAYS = 30;

function getDelayEvents(history: DisruptionEvent[], supplierId: string): DisruptionEvent[] {
  const supplierEvents = history.filter(
    (e) => Array.isArray(e.affected_suppliers) && e.affected_suppliers.includes(supplierId)
  );
  return supplierEvents.filter((e) => {
    const delay = (e.impact && e.impact.delay_days != null) ? Number(e.impact.delay_days) : 0;
    return delay > 0;
  });
}

/**
 * Compute disruption probability for one supplier using the same model as risk_tools.get_disruption_probability.
 */
export function computeSupplierDisruptionProbability(
  supplier: SupplierProfile,
  history: DisruptionEvent[],
  activeDisruption: ActiveDisruptionConfig,
  timeHorizonDays: number = TIME_HORIZON_DAYS
): SupplierRiskResult {
  const supplierId = supplier.id;
  const supplierName = (supplier.name as string) || supplierId;
  const region = ((supplier.country as string) || "Unknown").toLowerCase();
  let healthScore = supplier.health_score != null ? Number(supplier.health_score) : 75;
  const singleSource = !!supplier.single_source;
  const spendPct = Number(supplier.spend_pct) || 0;

  healthScore = Math.max(0, Math.min(100, Math.round(healthScore)));

  // Lane disrupted from config
  let laneDisrupted = false;
  let laneSeverity = "Low";
  const lanes = activeDisruption.shipping_lanes ?? {};
  for (const laneData of Object.values(lanes)) {
    if (laneData && typeof laneData === "object" && (laneData as { status?: string }).status === "DISRUPTED") {
      laneDisrupted = true;
      laneSeverity = (laneData as { severity?: string }).severity ?? "High";
      break;
    }
  }

  // 1. Delivery delay frequency
  const supplierEvents = history.filter(
    (e) => Array.isArray(e.affected_suppliers) && e.affected_suppliers.includes(supplierId)
  );
  const delayEvents = getDelayEvents(history, supplierId);
  const totalEvents = Math.max(supplierEvents.length, 1);
  const deliveryDelayFrequency = Math.min(1, (delayEvents.length / totalEvents) * 2);

  // 2. Financial health risk (invert)
  const financialHealthRisk = 1 - healthScore / 100;

  // 3. Region instability (no external news/climate in dashboard; use base geopolitical for Taiwan/Vietnam)
  let regionInstability = 0;
  if (region.includes("taiwan") || region.includes("vietnam")) {
    regionInstability = Math.min(1, 0.2);
  }

  // 4. Logistics congestion
  const logisticsCongestion =
    laneDisrupted && laneSeverity === "High" ? 0.7 : laneDisrupted ? 0.4 : 0;

  // 5. Weather (no climate feed in dashboard; keep 0 unless we add it later)
  const weatherDisruptionProb = 0;

  // Weighted probability (same weights as Python)
  const wHealth = 0.25;
  const wRegion = 0.25;
  const wLogistics = 0.25;
  const wDelivery = 0.15;
  const wWeather = 0.1;
  let pDisruption =
    wHealth * financialHealthRisk +
    wRegion * regionInstability +
    wLogistics * logisticsCongestion +
    wDelivery * deliveryDelayFrequency +
    wWeather * weatherDisruptionProb;
  if (singleSource) pDisruption = Math.min(1, pDisruption * 1.15);
  if (spendPct > 35) pDisruption = Math.min(1, pDisruption * 1.1);
  const disruptionProbabilityPct = Math.round(pDisruption * 100 * 10) / 10;

  // Classification (same thresholds as Python)
  const riskClassification: "Low" | "Medium" | "High" =
    disruptionProbabilityPct < 35 ? "Low" : disruptionProbabilityPct < 65 ? "Medium" : "High";

  // Primary drivers
  const primaryDrivers: string[] = [];
  if (financialHealthRisk > 0.4) {
    primaryDrivers.push(`Supplier financial health score (${healthScore}/100)`);
  }
  if (regionInstability > 0.3) {
    primaryDrivers.push(`Region instability / geopolitical exposure (${supplier.country ?? "N/A"})`);
  }
  if (logisticsCongestion > 0.3) {
    primaryDrivers.push("Logistics congestion / shipping lane disruption");
  }
  if (deliveryDelayFrequency > 0.3) {
    primaryDrivers.push(`Historical delivery delay frequency (${delayEvents.length} events)`);
  }
  if (weatherDisruptionProb > 0.2) {
    primaryDrivers.push("Weather / natural disaster alerts in region");
  }
  if (singleSource) {
    primaryDrivers.push("Single-source supplier (no qualified backup)");
  }
  if (spendPct > 35) {
    primaryDrivers.push(`High spend concentration (${spendPct}%)`);
  }
  if (primaryDrivers.length === 0) {
    primaryDrivers.push("Baseline risk from profile and history");
  }

  return {
    supplier_id: supplierId,
    supplier_name: supplierName,
    time_horizon_days: timeHorizonDays,
    disruption_probability_pct: disruptionProbabilityPct,
    risk_classification: riskClassification,
    primary_drivers: primaryDrivers,
    risk_indicators: {
      supplier_delivery_delay_frequency: Math.round(deliveryDelayFrequency * 1000) / 1000,
      supplier_financial_health_score: healthScore,
      region_instability_index: Math.round(regionInstability * 1000) / 1000,
      logistics_congestion_score: Math.round(logisticsCongestion * 1000) / 1000,
      weather_disruption_probability: Math.round(weatherDisruptionProb * 1000) / 1000,
    },
  };
}

/**
 * Compute risk for all suppliers and return aggregate score (max of supplier probabilities)
 * for use as disruptionRisk / overallSupplyRisk, plus per-supplier results for the UI.
 */
export function computeDashboardRisk(
  suppliers: SupplierProfile[],
  history: DisruptionEvent[],
  activeDisruption: ActiveDisruptionConfig,
  timeHorizonDays: number = TIME_HORIZON_DAYS
): { supplierRisks: SupplierRiskResult[]; aggregateDisruptionRiskPct: number } {
  const supplierRisks = suppliers.map((s) =>
    computeSupplierDisruptionProbability(s, history, activeDisruption, timeHorizonDays)
  );
  const aggregateDisruptionRiskPct =
    supplierRisks.length === 0
      ? 0
      : Math.round(Math.max(...supplierRisks.map((r) => r.disruption_probability_pct)));
  return { supplierRisks, aggregateDisruptionRiskPct };
}
