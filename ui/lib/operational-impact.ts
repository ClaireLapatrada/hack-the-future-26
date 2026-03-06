/**
 * Operational impact modeling for the dashboard.
 * Estimates how disruption propagates: production downtime probability,
 * affected lines, delay range, critical dependencies.
 * Mirrors tools/operational_impact_tools.py logic.
 */

export type InventoryItem = {
  item_id: string;
  supplier_id: string;
  days_on_hand?: number;
  daily_consumption?: number;
  [k: string]: unknown;
};

export type ProductionLine = {
  line_id: string;
  product: string;
  semiconductor_dependent?: boolean;
  daily_revenue_usd?: number;
  [k: string]: unknown;
};

export type Supplier = {
  id: string;
  single_source?: boolean;
  [k: string]: unknown;
};

export type ActiveDisruptionConfig = {
  active?: boolean;
  shipping_lanes?: Record<string, { status?: string; avg_delay_days?: number; [k: string]: unknown }>;
};

export type OperationalImpactResult = {
  productionDowntimeProbabilityPct: number;
  affectedProductionLines: Array<{ line_id: string; product: string; daily_revenue_usd: number; at_risk: boolean }>;
  estimatedDelayDaysMin: number;
  estimatedDelayDaysMax: number;
  criticalDependencies: Array<{ item_id: string; supplier_id: string; single_source: boolean; line_id: string }>;
};

const SIMULATION_RUNS = 300;

function seededRandom(seed: number): () => number {
  return () => {
    seed = (seed * 9301 + 49297) % 233280;
    return seed / 233280;
  };
}

export function computeOperationalImpact(
  inventory: InventoryItem[],
  productionLines: ProductionLine[],
  suppliers: Supplier[],
  activeDisruption: ActiveDisruptionConfig
): OperationalImpactResult {
  const singleSourceIds = new Set(suppliers.filter((s) => s.single_source).map((s) => s.id));

  const lineToItems: Record<string, InventoryItem[]> = {};
  for (const line of productionLines) {
    const sem = !!line.semiconductor_dependent;
    const items = inventory.filter(
      (inv) =>
        (sem && (inv.item_id || "").includes("SEMI")) ||
        (!sem && (inv.item_id || "").includes("STEEL"))
    );
    lineToItems[line.line_id || ""] = items;
  }

  const criticalDependencies: OperationalImpactResult["criticalDependencies"] = [];
  for (const [lineId, items] of Object.entries(lineToItems)) {
    for (const inv of items) {
      criticalDependencies.push({
        item_id: inv.item_id || "",
        supplier_id: inv.supplier_id || "",
        single_source: singleSourceIds.has(inv.supplier_id || ""),
        line_id: lineId,
      });
    }
  }

  const atRiskLineIds = new Set(
    criticalDependencies.filter((d) => d.single_source).map((d) => d.line_id)
  );

  let delayMin = 5;
  let delayMax = 15;
  if (activeDisruption.active && activeDisruption.shipping_lanes) {
    const delays: number[] = [];
    for (const v of Object.values(activeDisruption.shipping_lanes)) {
      if (v && (v as { status?: string }).status === "DISRUPTED") {
        const d = (v as { avg_delay_days?: number }).avg_delay_days;
        if (typeof d === "number") delays.push(d);
      }
    }
    if (delays.length > 0) {
      delayMin = Math.min(...delays);
      delayMax = Math.max(...delays);
    }
  }

  const rng = seededRandom(42);
  let shutdownCount = 0;
  const delaySamples: number[] = [];
  for (let i = 0; i < SIMULATION_RUNS; i++) {
    const disruptionDays =
      delayMin === delayMax ? delayMin : delayMin + Math.floor(rng() * (delayMax - delayMin + 1));
    delaySamples.push(disruptionDays);
    let runShutdown = false;
    for (const lineId of atRiskLineIds) {
      const items = lineToItems[lineId] || [];
      for (const inv of items) {
        if (!singleSourceIds.has(inv.supplier_id || "")) continue;
        const daysOnHand = inv.days_on_hand ?? 0;
        if (daysOnHand < disruptionDays) {
          runShutdown = true;
          break;
        }
      }
      if (runShutdown) break;
    }
    if (runShutdown) shutdownCount++;
  }

  const productionDowntimeProbabilityPct = Math.round(
    (100 * shutdownCount) / SIMULATION_RUNS
  );
  const affectedProductionLines = productionLines.map((line) => ({
    line_id: line.line_id || "",
    product: line.product || "",
    daily_revenue_usd: line.daily_revenue_usd ?? 0,
    at_risk: atRiskLineIds.has(line.line_id || ""),
  }));

  return {
    productionDowntimeProbabilityPct,
    affectedProductionLines,
    estimatedDelayDaysMin: delaySamples.length ? Math.min(...delaySamples) : delayMin,
    estimatedDelayDaysMax: delaySamples.length ? Math.max(...delaySamples) : delayMax,
    criticalDependencies,
  };
}
