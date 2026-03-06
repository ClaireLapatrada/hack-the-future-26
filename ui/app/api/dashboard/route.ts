import { NextResponse } from "next/server";
import path from "path";
import fs from "fs";
import { fetchNewsDisruptions } from "../../../lib/news-disruptions";

const DATA_ROOT = process.cwd();

function readJson<T>(filename: string): T {
  const filePath = path.join(DATA_ROOT, filename);
  const raw = fs.readFileSync(filePath, "utf-8");
  return JSON.parse(raw) as T;
}

/** Read active_disruption from repo root (../config) if present, else ui/config. */
function readActiveDisruptionConfig(): ActiveDisruptionConfig {
  const parentPath = path.join(DATA_ROOT, "..", "config", "active_disruption.json");
  const localPath = path.join(DATA_ROOT, "config", "active_disruption.json");
  for (const p of [parentPath, localPath]) {
    try {
      if (fs.existsSync(p)) {
        const raw = fs.readFileSync(p, "utf-8");
        return JSON.parse(raw) as ActiveDisruptionConfig;
      }
    } catch {
      continue;
    }
  }
  return { active: false, supplier_health_degraded: false, shipping_lanes: {} };
}

type DisruptionEvent = {
  event_id: string;
  date: string;
  type: string;
  region: string;
  severity: string;
  affected_suppliers?: string[];
  description: string;
  impact?: {
    delay_days?: number | null;
    revenue_at_risk_usd?: number | null;
    actual_revenue_lost_usd?: number | null;
  };
  mitigation_taken?: {
    action: string;
    cost_usd?: number | null;
    outcome: string;
  };
  lessons_learned?: string;
  logged_by?: string;
  logged_at?: string;
};

type ManufacturerProfile = {
  suppliers: Array<{
    id: string;
    name: string;
    spend_pct?: number;
    single_source?: boolean;
    health_score?: number;
    [k: string]: unknown;
  }>;
  inventory_policy?: { target_buffer_days: number; reorder_threshold_days: number; max_buffer_days: number };
  customer_slas?: Array<{ customer: string; on_time_delivery_pct: number; penalty_per_day_usd: number }>;
  production_lines?: Array<{ line_id: string; product: string; daily_output_units: number; daily_revenue_usd: number; [k: string]: unknown }>;
};

type MockErp = {
  inventory?: unknown[];
  open_purchase_orders?: unknown[];
};

type ActiveDisruptionConfig = {
  active: boolean;
  supplier_health_degraded?: boolean;
  shipping_lanes?: Record<string, unknown>;
};

export async function GET() {
  try {
    const realItems = await fetchNewsDisruptions();
    if (realItems.length > 0) {
      const profile = readJson<ManufacturerProfile>("config/manufacturer_profile.json");
      const erp = readJson<MockErp>("data/mock_erp.json");
      const suppliers = profile.suppliers ?? [];
      const singleSourceSuppliers = suppliers.filter((s) => s.single_source === true);
      const maxSpendPct = suppliers.length === 0 ? 0 : Math.max(0, ...suppliers.map((s) => Number(s.spend_pct) || 0));
      const criticalCount = realItems.filter((d) => d.severity === "CRITICAL").length;
      const highCount = realItems.filter((d) => d.severity === "HIGH").length;
      const disruptionRiskScore = Math.min(
        100,
        Math.round(criticalCount * 15 + highCount * 8 + Math.min(30, realItems.length * 5))
      );
      const disruptionList = realItems.slice(0, 20).map((d) => ({
        id: d.id,
        severity: d.severity,
        title: d.title,
        status: "Monitoring",
        age: "Recent",
      }));
      const kpis = {
        disruptionRisk: disruptionRiskScore,
        revenueAtRisk: 0,
        activeDisruptions: realItems.length,
        pendingApprovals: 0,
        overallSupplyRisk: disruptionRiskScore,
        logisticsFreight: Math.min(100, realItems.length * 25),
        supplierConcentration: Math.min(100, Math.max(0, Math.round(0 + maxSpendPct + singleSourceSuppliers.length * 40))),
        suppliers: profile.suppliers?.length ?? 0,
        inventoryPolicy: profile.inventory_policy,
        openPOs: erp.open_purchase_orders?.length ?? 0,
        disruptionRiskTrendPct: 0,
        revenueTrendPct: 0,
        activeDisruptionsTrendPct: 0,
        pendingApprovalsTrendPct: 0,
      };
      return NextResponse.json({ disruptions: disruptionList, kpis });
    }

    const disruptions = readJson<DisruptionEvent[]>("data/mock_disruption_history.json");
    const profile = readJson<ManufacturerProfile>("config/manufacturer_profile.json");
    const erp = readJson<MockErp>("data/mock_erp.json");
    const activeDisruption = readActiveDisruptionConfig();

    const lanes = activeDisruption.shipping_lanes ?? {};
    const disruptedLanes = Object.entries(lanes).filter(
      (entry): entry is [string, Record<string, unknown>] =>
        typeof entry[1] === "object" && entry[1] != null && (entry[1] as { status?: string }).status === "DISRUPTED"
    );
    const initiatedEvents: DisruptionEvent[] =
      disruptedLanes.length > 0
        ? disruptedLanes.map(([laneName, data]) => {
            const d = data as { avg_delay_days?: number; severity?: string };
            const delayDays = typeof d.avg_delay_days === "number" ? d.avg_delay_days : 14;
            const severity = (d.severity as string) ?? "High";
            return {
              event_id: "initiated-" + laneName.replace(/\s+/g, "-").toLowerCase().replace(/[^a-z0-9-]/g, ""),
              date: new Date().toISOString().slice(0, 10),
              type: "Shipping Disruption",
              region: laneName,
              severity,
              description: `${laneName} disrupted — ${delayDays} day delay (initiated for demo).`,
              impact: { delay_days: delayDays },
            };
          })
        : [];

    const useDisruptions = activeDisruption.active;
    const effectiveDisruptions =
      useDisruptions && initiatedEvents.length > 0 ? initiatedEvents : useDisruptions ? disruptions : [];
    const activeCount = effectiveDisruptions.length;
    let resolutions: Record<string, string> = {};
    try {
      const resPath =
        fs.existsSync(path.join(DATA_ROOT, "data/approval_resolutions.json"))
          ? path.join(DATA_ROOT, "data/approval_resolutions.json")
          : path.join(DATA_ROOT, "ui/data/approval_resolutions.json");
      if (fs.existsSync(resPath)) {
        resolutions = JSON.parse(fs.readFileSync(resPath, "utf-8")) as Record<string, string>;
      }
    } catch {
      // ignore
    }
    const pendingFromMock = useDisruptions
      ? disruptions.filter(
          (d) => d.mitigation_taken?.outcome === "Pending" && !resolutions[d.event_id]
        ).length
      : 0;
    let agentPendingCount = 0;
    try {
      const pendingPath =
        fs.existsSync(path.join(DATA_ROOT, "data/pending_approvals.json"))
          ? path.join(DATA_ROOT, "data/pending_approvals.json")
          : path.join(DATA_ROOT, "ui/data/pending_approvals.json");
      if (fs.existsSync(pendingPath)) {
        const raw = JSON.parse(fs.readFileSync(pendingPath, "utf-8")) as Array<{ status?: string }>;
        agentPendingCount = Array.isArray(raw)
          ? raw.filter((e) => e.status === "pending" || e.status === undefined).length
          : 0;
      }
    } catch {
      // ignore
    }
    const pendingCount = pendingFromMock + agentPendingCount;
    const totalRevenueAtRisk = useDisruptions
      ? disruptions.reduce((sum, d) => {
          const v = d.impact?.revenue_at_risk_usd;
          return sum + (typeof v === "number" && !Number.isNaN(v) ? v : 0);
        }, 0)
      : 0;

    const criticalCount = effectiveDisruptions.filter(
      (d) => String(d.severity).toUpperCase() === "CRITICAL"
    ).length;
    const highCount = effectiveDisruptions.filter(
      (d) => String(d.severity).toUpperCase() === "HIGH"
    ).length;
    const logisticsKeywords = ["shipping", "suez", "red sea", "canal", "freight", "vessel", "port"];
    const logisticsCount = effectiveDisruptions.filter((d) =>
      logisticsKeywords.some(
        (k) =>
          (d.type?.toLowerCase() ?? "").includes(k) ||
          (d.region?.toLowerCase() ?? "").includes(k) ||
          (d.description?.toLowerCase() ?? "").includes(k)
      )
    ).length;

    const disruptionRiskScore =
      activeCount === 0
        ? 0
        : Math.min(
            100,
            Math.round(
              criticalCount * 15 +
                highCount * 8 +
                (pendingCount / Math.max(activeCount, 1)) * 20 +
                Math.min(20, totalRevenueAtRisk / 1_000_000)
            )
          );

    const logisticsFreightScore =
      activeCount > 0 ? Math.min(100, Math.round((logisticsCount / activeCount) * 100)) : 0;

    const suppliers = profile.suppliers ?? [];
    const singleSourceSuppliers = suppliers.filter((s) => s.single_source === true);
    const maxSpendPct = suppliers.length === 0 ? 0 : Math.max(0, ...suppliers.map((s) => Number(s.spend_pct) || 0));
    const supplierConcentrationScore = Math.min(
      100,
      Math.max(0, Math.round(0 + maxSpendPct + singleSourceSuppliers.length * 40 + (activeDisruption.supplier_health_degraded ? 15 : 0)))
    );

    const disruptionList = effectiveDisruptions.slice(0, 20).map((d) => ({
      id: d.event_id,
      severity: d.severity === "CRITICAL" ? "CRITICAL" : d.severity === "High" ? "HIGH" : d.severity === "Medium" ? "MEDIUM" : "LOW",
      title: d.description.slice(0, 80) + (d.description.length > 80 ? "…" : ""),
      status: d.mitigation_taken?.outcome === "Pending" ? "Investigating" : "Mitigating",
      age: formatAge(d.date, d.logged_at),
    }));

    const kpis = {
      disruptionRisk: disruptionRiskScore,
      revenueAtRisk: totalRevenueAtRisk,
      activeDisruptions: activeCount,
      pendingApprovals: pendingCount,
      overallSupplyRisk: disruptionRiskScore,
      logisticsFreight: logisticsFreightScore,
      supplierConcentration: supplierConcentrationScore,
      suppliers: profile.suppliers?.length ?? 0,
      inventoryPolicy: profile.inventory_policy,
      openPOs: erp.open_purchase_orders?.length ?? 0,
      disruptionRiskTrendPct: pendingCount > 0 ? Math.min(15, 5 + pendingCount * 4) : 0,
      revenueTrendPct: totalRevenueAtRisk > 0 ? Math.min(15, 5 + Math.floor(totalRevenueAtRisk / 500_000)) : 0,
      activeDisruptionsTrendPct: 0,
      pendingApprovalsTrendPct: 0,
    };

    return NextResponse.json({
      disruptions: disruptionList,
      kpis,
    });
  } catch (e) {
    console.error("Failed to load dashboard data:", e);
    return NextResponse.json(
      { error: "Failed to load dashboard data" },
      { status: 500 }
    );
  }
}

function formatAge(dateStr: string, loggedAt?: string): string {
  const dt = loggedAt ? new Date(loggedAt) : new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - dt.getTime();
  const diffM = Math.floor(diffMs / 60000);
  const diffH = Math.floor(diffM / 60);
  const diffD = Math.floor(diffH / 24);
  if (diffM < 60) return `${diffM} min ago`;
  if (diffH < 24) return `${diffH}h ago`;
  if (diffD < 30) return `${diffD}d ago`;
  return `${dateStr}`;
}
