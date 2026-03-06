import { NextResponse } from "next/server";
import path from "path";
import fs from "fs";

const DATA_ROOT = process.cwd();

function readJson<T>(filePath: string): T {
  const raw = fs.readFileSync(filePath, "utf-8");
  return JSON.parse(raw) as T;
}

function readPlanningConfig() {
  const p = path.join(DATA_ROOT, "..", "planning_config.json");
  if (!fs.existsSync(p)) {
    throw new Error("planning_config.json not found");
  }
  return readJson<{
    scenario_definitions: Record<
      string,
      {
        name: string;
        description: string;
        base_unit_cost_usd: number;
        unit_cost_premium_pct: number;
        fixed_cost_usd: number;
        implementation_days: number;
        lead_time_reduction_days: number;
        service_level_protection: string;
        risks: string[];
        co2_impact: string;
      }
    >;
    risk_appetite_weights: Record<string, { service: number; cost: number; speed: number }>;
    service_level_scores: Record<string, number>;
    rank_service_scores: Record<string, number>;
  }>(p);
}

type DisruptionEvent = {
  event_id: string;
  impact?: { delay_days?: number | null };
  affected_suppliers?: string[];
  description?: string;
};

type ErpInventoryItem = {
  item_id: string;
  supplier_id: string;
  days_on_hand: number;
  daily_consumption: number;
  stock_units?: number;
};

type MockErp = { inventory?: ErpInventoryItem[] };

/** Simulate one scenario (mirrors tools/planning_tools.simulate_mitigation_scenario). */
function simulateScenario(
  config: Awaited<ReturnType<typeof readPlanningConfig>>,
  scenario: {
    name: string;
    description: string;
    base_unit_cost_usd: number;
    unit_cost_premium_pct: number;
    fixed_cost_usd: number;
    implementation_days: number;
    lead_time_reduction_days: number;
    service_level_protection: string;
    risks: string[];
    co2_impact: string;
  },
  scenarioType: string,
  quantityNeeded: number
) {
  const premiumUnitCost =
    scenario.base_unit_cost_usd * (1 + scenario.unit_cost_premium_pct / 100);
  const variableCost = premiumUnitCost * quantityNeeded;
  const totalCost = variableCost + scenario.fixed_cost_usd;
  const baselineCost = scenario.base_unit_cost_usd * quantityNeeded;
  const incrementalCost = totalCost - baselineCost;

  const serviceLevelScore =
    config.service_level_scores?.[scenario.service_level_protection] ?? 50;
  const costScore = Math.max(0, 100 - scenario.unit_cost_premium_pct / 3);
  const speedScore = Math.max(0, 100 - scenario.implementation_days * 4);
  const compositeScore =
    serviceLevelScore * 0.5 + costScore * 0.3 + speedScore * 0.2;

  return {
    scenario_type: scenarioType,
    scenario_name: scenario.name,
    description: scenario.description,
    financials: {
      incremental_cost_usd: Math.round(incrementalCost * 100) / 100,
      total_cost_usd: Math.round(totalCost * 100) / 100,
      unit_cost_premium_pct: scenario.unit_cost_premium_pct,
    },
    timing: {
      implementation_days: scenario.implementation_days,
      lead_time_change_days: scenario.lead_time_reduction_days,
    },
    service_level_protection: scenario.service_level_protection,
    composite_score: Math.round(compositeScore * 10) / 10,
  };
}

/** Rank scenarios by risk appetite (mirrors tools/planning_tools.rank_scenarios). */
function rankScenarios(
  config: Awaited<ReturnType<typeof readPlanningConfig>>,
  scenarios: Array<{
    scenario_type: string;
    scenario_name: string;
    description?: string;
    financials?: {
      unit_cost_premium_pct?: number;
      incremental_cost_usd?: number;
    };
    timing?: { implementation_days?: number };
    service_level_protection?: string;
  }>,
  riskAppetite: string
) {
  const w = config.risk_appetite_weights?.[riskAppetite] ?? config.risk_appetite_weights?.low ?? { service: 0.6, cost: 0.25, speed: 0.15 };
  const rankScores = config.rank_service_scores ?? { High: 100, Medium: 60, Low: 20 };

  const ranked = scenarios.map((s) => {
    const serviceScore = rankScores[s.service_level_protection ?? "Low"] ?? 20;
    const costScore = Math.max(
      0,
      100 - (s.financials?.unit_cost_premium_pct ?? 0) / 3
    );
    const speedScore = Math.max(
      0,
      100 - (s.timing?.implementation_days ?? 30) * 3
    );
    const adjustedScore =
      serviceScore * w.service + costScore * w.cost + speedScore * w.speed;
    return { ...s, adjusted_score: Math.round(adjustedScore * 10) / 10 };
  });

  ranked.sort((a, b) => (b as { adjusted_score: number }).adjusted_score - (a as { adjusted_score: number }).adjusted_score);
  return ranked;
}

export async function POST(req: Request) {
  try {
    const body = await req.json().catch(() => ({}));
    const eventId = (body.eventId ?? body.event_id) as string | undefined;
    const bufferDays = typeof body.bufferDays === "number" ? body.bufferDays : 14;
    const riskAppetite =
      body.riskAppetite === "medium" || body.riskAppetite === "high"
        ? body.riskAppetite
        : "low";

    const config = readPlanningConfig();
    const scenariosDef = config.scenario_definitions ?? {};
    const scenarioTypes = ["airfreight", "buffer_build", "alternate_supplier"];

    let disruptionDays = 10;
    let affectedItemId = "SEMI-MCU-32";
    let quantityNeeded = 4000;

    if (eventId) {
      const disruptionsPath = path.join(
        DATA_ROOT,
        "data",
        "mock_disruption_history.json"
      );
      const erpPath = path.join(DATA_ROOT, "data", "mock_erp.json");
      if (fs.existsSync(disruptionsPath)) {
        const events = readJson<DisruptionEvent[]>(disruptionsPath);
        const event = events.find((e) => e.event_id === eventId);
        if (event?.impact?.delay_days != null) {
          disruptionDays = event.impact.delay_days;
        }
      }
      if (fs.existsSync(erpPath)) {
        const erp = readJson<MockErp>(erpPath);
        const inventory = erp.inventory ?? [];
        const item = inventory.find(
          (i) => i.daily_consumption && i.daily_consumption > 0
        ) as ErpInventoryItem | undefined;
        if (item) {
          affectedItemId = item.item_id;
          const dailyConsumption = item.daily_consumption;
          quantityNeeded = Math.max(
            1000,
            Math.ceil(disruptionDays * dailyConsumption * 0.8)
          );
        }
      }
    }

    const simulated = scenarioTypes
      .filter((t) => scenariosDef[t])
      .map((t) =>
        simulateScenario(config, scenariosDef[t], t, quantityNeeded)
      );

    const ranked = rankScenarios(config, simulated, riskAppetite);
    const top = ranked[0];

    return NextResponse.json({
      eventId: eventId ?? null,
      bufferDays,
      riskAppetite,
      affectedItemId,
      disruptionDays,
      quantityNeeded,
      rankedScenarios: ranked.map((s) => ({
        scenarioType: s.scenario_type,
        scenarioName: s.scenario_name,
        description: s.description,
        incrementalCostUsd: s.financials?.incremental_cost_usd,
        implementationDays: s.timing?.implementation_days,
        serviceLevelProtection: s.service_level_protection,
        adjustedScore: (s as { adjusted_score?: number }).adjusted_score,
      })),
      topRecommendation: top
        ? {
            scenarioName: top.scenario_name,
            incrementalCostUsd: top.financials?.incremental_cost_usd,
            implementationDays: top.timing?.implementation_days,
            serviceLevelProtection: top.service_level_protection,
          }
        : null,
    });
  } catch (e) {
    console.error("Scenario run failed:", e);
    return NextResponse.json(
      {
        error:
          e instanceof Error ? e.message : "Failed to run scenario simulation",
      },
      { status: 500 }
    );
  }
}
