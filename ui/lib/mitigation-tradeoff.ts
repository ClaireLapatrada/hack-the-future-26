/**
 * Mitigation trade-off summary for the dashboard.
 * Mirrors tools/planning_tools.evaluate_mitigation_tradeoffs logic using scenario_definitions.
 */

export type ScenarioDef = {
  name: string;
  unit_cost_premium_pct: number;
  base_unit_cost_usd: number;
  fixed_cost_usd: number;
  service_level_protection: string;
  implementation_days: number;
};

export type PlanningConfig = {
  scenario_definitions?: Record<string, ScenarioDef>;
  risk_appetite_weights?: Record<string, { service: number; cost: number; speed: number }>;
  rank_service_scores?: Record<string, number>;
};

export type MitigationTradeoffResult = {
  recommendedStrategy: string;
  scenarios: Array<{ name: string; costUsd: number; serviceLevel: string; resilienceNote: string; adjustedScore: number }>;
  costVsResilience: string[];
  serviceLevelImpact: string;
  summary: string;
};

const SCENARIO_KEYS = ["buffer_build", "alternate_supplier", "airfreight"] as const;

export function computeMitigationTradeoff(
  config: PlanningConfig,
  disruptionDays: number = 10,
  quantityNeeded: number = 5000,
  riskAppetite: string = "medium"
): MitigationTradeoffResult {
  const scenarios = config.scenario_definitions ?? {};
  const weights = config.risk_appetite_weights?.[riskAppetite] ?? config.risk_appetite_weights?.medium ?? { service: 0.45, cost: 0.35, speed: 0.2 };
  const rankScores = config.rank_service_scores ?? { High: 100, Medium: 60, Low: 20 };

  const simulated: Array<{
    scenario_type: string;
    scenario_name: string;
    financials: { incremental_cost_usd: number; total_cost_usd: number; unit_cost_premium_pct: number };
    timing: { implementation_days: number };
    service_level_protection: string;
    adjusted_score: number;
  }> = [];

  for (const key of SCENARIO_KEYS) {
    const sc = scenarios[key];
    if (!sc) continue;
    const premiumUnit = sc.base_unit_cost_usd * (1 + sc.unit_cost_premium_pct / 100);
    const variableCost = premiumUnit * quantityNeeded;
    const totalCost = variableCost + sc.fixed_cost_usd;
    const baselineCost = sc.base_unit_cost_usd * quantityNeeded;
    const incrementalCost = totalCost - baselineCost;

    const serviceScore = rankScores[sc.service_level_protection as keyof typeof rankScores] ?? 60;
    const costScore = Math.max(0, 100 - sc.unit_cost_premium_pct / 3);
    const speedScore = Math.max(0, 100 - sc.implementation_days * 3);
    const adjustedScore =
      serviceScore * weights.service + costScore * weights.cost + speedScore * weights.speed;

    simulated.push({
      scenario_type: key,
      scenario_name: sc.name,
      financials: {
        incremental_cost_usd: incrementalCost,
        total_cost_usd: totalCost,
        unit_cost_premium_pct: sc.unit_cost_premium_pct,
      },
      timing: { implementation_days: sc.implementation_days },
      service_level_protection: sc.service_level_protection,
      adjusted_score: adjustedScore,
    });
  }

  simulated.sort((a, b) => b.adjusted_score - a.adjusted_score);
  const top = simulated[0];
  const recommendedStrategy = top?.scenario_name ?? "—";
  const serviceLevelImpact = top?.service_level_protection ?? "Medium";

  const scenariosForOutput = simulated.map((r) => ({
    name: r.scenario_name,
    costUsd: Math.round(r.financials.incremental_cost_usd * 100) / 100,
    serviceLevel: r.service_level_protection,
    resilienceNote: r.service_level_protection === "High" ? "High" : r.service_level_protection === "Medium" ? "Medium" : "Lower",
    adjustedScore: Math.round(r.adjusted_score * 10) / 10,
  }));

  const costVsResilience = simulated.map(
    (r) => `${r.scenario_name}: $${(r.financials.incremental_cost_usd / 1e3).toFixed(0)}K cost, ${r.service_level_protection === "High" ? "High" : r.service_level_protection === "Medium" ? "Medium" : "Lower"} resilience`
  );

  const summary =
    `Recommended mitigation: ${recommendedStrategy}. ` +
    `Cost vs resilience: ${costVsResilience.join("; ")}. ` +
    `Expected service-level impact: ${serviceLevelImpact} protection.`;

  return {
    recommendedStrategy,
    scenarios: scenariosForOutput,
    costVsResilience,
    serviceLevelImpact,
    summary,
  };
}
