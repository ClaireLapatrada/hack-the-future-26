/**
 * Revenue-at-risk executive summary for the dashboard.
 * Mirrors tools/risk_tools.estimate_revenue_at_risk_executive logic.
 */

export type OperationalImpactForRevenue = {
  affectedProductionLines: Array<{ line_id: string; product: string; daily_revenue_usd: number; at_risk: boolean }>;
  estimatedDelayDaysMin: number;
  estimatedDelayDaysMax: number;
};

export type ProfileForRevenue = {
  customer_slas?: Array<{ customer: string; penalty_per_day_usd?: number }>;
};

export type RevenueAtRiskExecutive = {
  revenueAtRiskUsd: number;
  marginImpactUsd: number;
  slaPenaltiesUsd: number;
  customersAffected: number;
  bestCase: { revenue_at_risk_usd: number; margin_impact_usd: number; sla_penalties_usd: number; delay_days: number };
  expectedCase: { revenue_at_risk_usd: number; margin_impact_usd: number; sla_penalties_usd: number; delay_days: number };
  worstCase: { revenue_at_risk_usd: number; margin_impact_usd: number; sla_penalties_usd: number; delay_days: number };
  summary: string;
};

const MARGIN_RATE = 0.3;

export function computeRevenueAtRiskExecutive(
  impact: OperationalImpactForRevenue,
  profile: ProfileForRevenue
): RevenueAtRiskExecutive {
  const lines = impact.affectedProductionLines ?? [];
  const delayMin = impact.estimatedDelayDaysMin ?? 5;
  const delayMax = impact.estimatedDelayDaysMax ?? 15;
  const delayMid = Math.floor((delayMin + delayMax) / 2);
  const customerSlas = profile.customer_slas ?? [];

  function outcome(delayDays: number) {
    const rev = lines
      .filter((l) => l.at_risk)
      .reduce((sum, l) => sum + (l.daily_revenue_usd ?? 0), 0) * delayDays;
    const sla = customerSlas.reduce((sum, s) => sum + (s.penalty_per_day_usd ?? 0), 0) * delayDays;
    const margin = rev * MARGIN_RATE;
    return {
      revenue_at_risk_usd: Math.round(rev * 100) / 100,
      sla_penalties_usd: Math.round(sla * 100) / 100,
      margin_impact_usd: Math.round(margin * 100) / 100,
      delay_days: delayDays,
    };
  }

  const best = outcome(delayMin);
  const expected = outcome(delayMid);
  const worst = outcome(delayMax);

  const revenueAtRiskUsd = expected.revenue_at_risk_usd;
  const marginImpactUsd = expected.margin_impact_usd;
  const slaPenaltiesUsd = expected.sla_penalties_usd;
  const customersAffected = customerSlas.length;

  const summary =
    `Revenue-at-risk: $${(revenueAtRiskUsd / 1e6).toFixed(1)}M (expected). ` +
    `Margin impact: $${(marginImpactUsd / 1e6).toFixed(1)}M. ` +
    `Customers affected: ${customersAffected} major OEM accounts. ` +
    `SLA penalty exposure: $${(slaPenaltiesUsd / 1e3).toFixed(0)}K.`;

  return {
    revenueAtRiskUsd,
    marginImpactUsd,
    slaPenaltiesUsd,
    customersAffected,
    bestCase: best,
    expectedCase: expected,
    worstCase: worst,
    summary,
  };
}
