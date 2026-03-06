"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { LayoutShell } from "../components/LayoutShell";
import { AgentReasoningStream, type StreamEntry } from "../components/AgentReasoningStream";
import { GlobalDisruptionMap } from "../components/GlobalDisruptionMap";
import { CalculationModal } from "../components/CalculationModal";
import { OperationalImpactGraph } from "../components/OperationalImpactGraph";

type DisruptionSummary = {
  id: string;
  severity: string;
  title: string;
  status: string;
  age: string;
};

type DashboardData = {
  disruptions: DisruptionSummary[];
  kpis: {
    disruptionRisk: number;
    revenueAtRisk: number;
    activeDisruptions: number;
    pendingApprovals: number;
    overallSupplyRisk: number;
    logisticsFreight: number;
    supplierConcentration: number;
    disruptionRiskTrendPct?: number;
    revenueTrendPct?: number;
    activeDisruptionsTrendPct?: number;
    pendingApprovalsTrendPct?: number;
  };
  supplierRisks?: Array<{
    supplier_id: string;
    supplier_name: string;
    time_horizon_days: number;
    disruption_probability_pct: number;
    risk_classification: "Low" | "Medium" | "High";
    primary_drivers: string[];
  }>;
  operationalImpact?: {
    productionDowntimeProbabilityPct: number;
    affectedProductionLines: Array<{ line_id: string; product: string; daily_revenue_usd: number; at_risk: boolean }>;
    estimatedDelayDaysMin: number;
    estimatedDelayDaysMax: number;
    criticalDependencies: Array<{ item_id: string; supplier_id: string; single_source: boolean; line_id: string }>;
  };
  allSuppliers?: Array<{ id: string; name: string }>;
  revenueAtRiskExecutive?: {
    revenueAtRiskUsd: number;
    marginImpactUsd: number;
    slaPenaltiesUsd: number;
    customersAffected: number;
    summary: string;
  };
};

function InfoIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor" aria-hidden>
      <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
    </svg>
  );
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [streamEntries, setStreamEntries] = useState<StreamEntry[]>([]);
  const [streamLoading, setStreamLoading] = useState(true);
  const [viewMode, setViewMode] = useState<"dashboard" | "map">("dashboard");
  const [streamExpanded, setStreamExpanded] = useState(false);
  const [calculationModal, setCalculationModal] = useState<"supplier-risk" | "overall-risk" | "operational-impact" | "operational-graph" | "revenue-at-risk" | null>(null);

  useEffect(() => {
    fetch("/api/dashboard")
      .then((res) => {
        if (!res.ok) throw new Error("Failed to load dashboard");
        return res.json();
      })
      .then(setData)
      .catch((e) => setLoadError(e instanceof Error ? e.message : "Failed to load"));
  }, []);

  useEffect(() => {
    const fetchStream = () => {
      fetch("/api/agent-stream?context=dashboard")
        .then((res) => {
          if (!res.ok) throw new Error("Failed to load agent stream");
          return res.json();
        })
        .then((entries: StreamEntry[]) => setStreamEntries(Array.isArray(entries) ? entries : []))
        .catch(() => setStreamEntries([]))
        .finally(() => setStreamLoading(false));
    };
    fetchStream();
    const interval = setInterval(fetchStream, 2500);
    return () => clearInterval(interval);
  }, []);

  const disruptions = data?.disruptions ?? [];
  const supplierRisks = data?.supplierRisks ?? [];
  const operationalImpact = data?.operationalImpact;
  const revenueAtRiskExecutive = data?.revenueAtRiskExecutive;
  const kpis = data?.kpis ?? {
    disruptionRisk: 0,
    revenueAtRisk: 0,
    activeDisruptions: 0,
    pendingApprovals: 0,
    overallSupplyRisk: 0,
    logisticsFreight: 0,
    supplierConcentration: 0,
    disruptionRiskTrendPct: 0,
    revenueTrendPct: 0,
    activeDisruptionsTrendPct: 0,
    pendingApprovalsTrendPct: 0,
  };

  const trendLabel = (pct: number) =>
    pct > 0 ? `↑ ${pct}% from last period` : pct < 0 ? `↓ ${Math.abs(pct)}% from last period` : "— 0% from last period";

  const revenueStr =
    kpis.revenueAtRisk >= 1_000_000
      ? `$${(kpis.revenueAtRisk / 1_000_000).toFixed(1)}M`
      : `$${(kpis.revenueAtRisk / 1_000).toFixed(0)}K`;

  const riskTier = (score: number) => {
    if (score >= 70) return { border: "border-danger/30", bg: "bg-danger/15", text: "text-danger", barBg: "bg-danger/30", barFill: "bg-danger" };
    if (score >= 40) return { border: "border-warning/30", bg: "bg-warning/15", text: "text-warning", barBg: "bg-warning/30", barFill: "bg-warning" };
    return { border: "border-success/30", bg: "bg-success/15", text: "text-success", barBg: "bg-success/30", barFill: "bg-success" };
  };

  const headerRight = (
    <div className="flex items-center gap-4">
      <div className="inline-flex rounded-md border border-white/10 bg-surfaceMuted text-[11px] font-mono">
        <button
          type="button"
          onClick={() => setViewMode("dashboard")}
          className={`px-3 py-1.5 ${
            viewMode === "dashboard" ? "bg-agentCyan text-background" : "text-textMuted"
          }`}
        >
          Dashboard
        </button>
        <button
          type="button"
          onClick={() => setViewMode("map")}
          className={`px-3 py-1.5 ${
            viewMode === "map" ? "bg-agentCyan text-background" : "text-textMuted"
          }`}
        >
          Map
        </button>
      </div>
      <div className="hidden items-center gap-2 font-mono text-xs text-textPrimary sm:flex">
        <span className="text-textMuted">Last sync:</span>
        <span>7:22:49 PM</span>
      </div>
    </div>
  );

  return (
    <LayoutShell
      title="Supply Chain Risk Dashboard"
      subtitle="Real-time disruption intelligence powered by Google ADK"
      headerRight={headerRight}
    >
      <div className="flex h-full min-h-0 flex-col gap-3 overflow-hidden">
        {viewMode === "dashboard" ? (
          <>
            {/* Risk pills: 3 pills full width — at top */}
            <section className="w-full shrink-0">
              <div className="grid grid-cols-3 gap-3">
                {(() => {
                  const t1 = riskTier(kpis.overallSupplyRisk);
                  const topDriver = supplierRisks.length > 0
                    ? supplierRisks.reduce((a, b) =>
                        a.disruption_probability_pct >= b.disruption_probability_pct ? a : b
                      )
                    : null;
                  return (
                    <div
                      className={`flex flex-1 cursor-pointer flex-col justify-center gap-1 rounded-lg border ${t1.border} ${t1.bg} px-3 py-2 font-mono text-[10px] transition-colors duration-300 hover:border-white/20`}
                      onClick={() => setCalculationModal("overall-risk")}
                      role="button"
                      tabIndex={0}
                      onKeyDown={(e) => e.key === "Enter" && setCalculationModal("overall-risk")}
                    >
                      <div className="flex items-baseline justify-between gap-1">
                        <span className={`font-medium ${t1.text}`}>Overall Supply Risk</span>
                        <span className={`flex items-center gap-0.5 text-lg font-semibold ${t1.text} transition-colors duration-300`}>
                          {kpis.overallSupplyRisk}%
                          <button
                            type="button"
                            onClick={(e) => { e.stopPropagation(); setCalculationModal("overall-risk"); }}
                            className="rounded p-0.5 text-textMuted hover:text-agentCyan focus:outline-none"
                            aria-label="How is this calculated?"
                          >
                            <InfoIcon className="h-3 w-3" />
                          </button>
                        </span>
                      </div>
                      <div className={`h-1 rounded-md ${t1.barBg}`}>
                        <div
                          className={`risk-pill-bar-fill h-full rounded-md ${t1.barFill}`}
                          style={{ width: `${Math.min(100, kpis.overallSupplyRisk)}%` }}
                        />
                      </div>
                      {topDriver && (
                        <p className="mt-0.5 text-[9px] text-textMuted leading-tight truncate" title={topDriver.primary_drivers.slice(0, 2).join("; ")}>
                          {topDriver.risk_classification} · {topDriver.primary_drivers[0] ?? ""}
                        </p>
                      )}
                    </div>
                  );
                })()}
                {(() => {
                  const impact = operationalImpact;
                  const pct = impact?.productionDowntimeProbabilityPct ?? 0;
                  const t2 = riskTier(pct);
                  const delayStr =
                    impact && impact.estimatedDelayDaysMin !== impact.estimatedDelayDaysMax
                      ? `${impact.estimatedDelayDaysMin}–${impact.estimatedDelayDaysMax}d`
                      : impact
                        ? `${impact.estimatedDelayDaysMin}d`
                        : "—";
                  const affectedNames =
                    impact?.affectedProductionLines.filter((l) => l.at_risk).map((l) => l.product || l.line_id) ?? [];
                  return (
                    <div
                      className={`flex flex-1 cursor-pointer flex-col justify-center gap-1 rounded-lg border ${t2.border} ${t2.bg} px-3 py-2 font-mono text-[10px] transition-colors duration-300 hover:border-white/20`}
                      onClick={() => setCalculationModal("operational-impact")}
                      role="button"
                      tabIndex={0}
                      onKeyDown={(e) => e.key === "Enter" && setCalculationModal("operational-impact")}
                    >
                      <div className="flex items-baseline justify-between gap-1">
                        <span className={`font-medium ${t2.text}`}>Operational Impact</span>
                        <span className={`flex items-center gap-0.5 text-lg font-semibold ${t2.text} transition-colors duration-300`}>
                          {pct}%
                          <button
                            type="button"
                            onClick={(e) => { e.stopPropagation(); setCalculationModal("operational-impact"); }}
                            className="rounded p-0.5 text-textMuted hover:text-agentCyan focus:outline-none"
                            aria-label="How is this calculated?"
                          >
                            <InfoIcon className="h-3 w-3" />
                          </button>
                        </span>
                      </div>
                      <div className={`h-1 rounded-md ${t2.barBg}`}>
                        <div
                          className={`risk-pill-bar-fill h-full rounded-md ${t2.barFill}`}
                          style={{ width: `${Math.min(100, pct)}%` }}
                        />
                      </div>
                      {impact && (
                        <p className="mt-0.5 text-[9px] text-textMuted leading-tight truncate" title={affectedNames.join(", ")}>
                          {affectedNames.length > 0 ? affectedNames[0] : "No lines at risk"} · {delayStr}
                        </p>
                      )}
                    </div>
                  );
                })()}
                {revenueAtRiskExecutive && (
                  <div
                    className="flex flex-1 cursor-pointer flex-col justify-center gap-1 rounded-lg border border-warning/30 bg-warning/15 px-3 py-2 font-mono text-[10px] transition-colors duration-300 hover:border-white/20"
                    onClick={() => setCalculationModal("revenue-at-risk")}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => e.key === "Enter" && setCalculationModal("revenue-at-risk")}
                  >
                    <div className="flex items-baseline justify-between gap-1">
                      <span className="font-medium text-warning">Revenue at Risk</span>
                      <span className="flex items-center gap-0.5 text-lg font-semibold text-warning">
                        {revenueAtRiskExecutive.revenueAtRiskUsd >= 1e6
                          ? `$${(revenueAtRiskExecutive.revenueAtRiskUsd / 1e6).toFixed(1)}M`
                          : `$${(revenueAtRiskExecutive.revenueAtRiskUsd / 1e3).toFixed(0)}K`}
                        <button
                          type="button"
                          onClick={(e) => { e.stopPropagation(); setCalculationModal("revenue-at-risk"); }}
                          className="rounded p-0.5 text-textMuted hover:text-agentCyan focus:outline-none"
                          aria-label="How is this calculated?"
                        >
                          <InfoIcon className="h-3 w-3" />
                        </button>
                      </span>
                    </div>
                    <p className="mt-0.5 text-[9px] text-textMuted leading-tight">
                      Margin: ${(revenueAtRiskExecutive.marginImpactUsd / 1e6).toFixed(1)}M · {revenueAtRiskExecutive.customersAffected} OEMs
                    </p>
                  </div>
                )}
              </div>
            </section>

            {/* Bottom row: Left = Active Disruptions (top) + Agent stream (bottom). Right = Supplier disruption (compact, top) + Supply network graph (below) */}
            <section className="grid min-h-0 min-h-[280px] flex-1 grid-cols-2 gap-4">
              <div className="flex min-h-0 flex-col gap-4">
                <div className="glass-card shrink-0 overflow-hidden p-4">
                  <div className="mb-2 flex items-center justify-between text-xs">
                    <span className="font-semibold">Active Disruptions</span>
                    <span className="flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-wide text-success">
                      <span className="h-1.5 w-1.5 rounded-md bg-success" />
                      Live
                    </span>
                  </div>
                  <div className="max-h-[180px] overflow-y-auto">
                    <div className="space-y-0">
                      {disruptions.map((d) => (
                        <Link
                          key={d.id}
                          href={`/disruptions?id=${encodeURIComponent(d.id)}`}
                          className="flex flex-wrap items-center justify-between gap-x-2 gap-y-1 border-b border-white/5 py-3 last:border-0 transition hover:bg-surfaceMuted/50"
                        >
                          <div className="flex min-w-0 flex-1 items-center gap-2">
                            <span
                              className={
                                d.severity === "CRITICAL"
                                  ? "pill-critical"
                                  : d.severity === "HIGH"
                                    ? "pill-high"
                                    : d.severity === "MEDIUM"
                                      ? "pill-medium-severity"
                                      : "pill-low"
                              }
                            >
                              {d.severity}
                            </span>
                            <span className="truncate text-xs font-medium">
                              {d.title}
                            </span>
                          </div>
                          <div className="flex shrink-0 items-center gap-3 text-[11px]">
                            <span className="font-mono text-textMuted">
                              {d.id} · {d.age}
                            </span>
                            <span className="text-textMuted">{d.status}</span>
                          </div>
                        </Link>
                      ))}
                    </div>
                  </div>
                </div>
                <div className="glass-card flex min-h-0 flex-1 flex-col overflow-hidden p-4">
                  <AgentReasoningStream
                    entries={streamEntries}
                    showCursorLabel={true}
                    title="Agent Reasoning Stream"
                    liveLabel={streamLoading ? "Loading…" : "Streaming"}
                  />
                </div>
              </div>

              <div className="flex min-h-0 flex-col gap-3">
                {/* Supplier disruption (30d) — compact, half height, above the graph */}
                <div
                  className="glass-card shrink-0 cursor-pointer overflow-hidden p-2.5 font-mono transition hover:border-white/15"
                  onClick={() => setCalculationModal("supplier-risk")}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => e.key === "Enter" && setCalculationModal("supplier-risk")}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[10px] font-medium uppercase tracking-wide text-textMuted">
                      Supplier disruption (30d)
                    </span>
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation(); setCalculationModal("supplier-risk"); }}
                      className="rounded p-0.5 text-textMuted hover:text-agentCyan focus:outline-none"
                      aria-label="How is this calculated?"
                    >
                      <InfoIcon className="h-3.5 w-3.5" />
                    </button>
                  </div>
                  {supplierRisks.length > 0 ? (
                    <ul className="mt-1.5 max-h-[100px] space-y-1 overflow-y-auto text-[11px]">
                      {supplierRisks.map((r) => (
                        <li key={r.supplier_id} className="flex items-baseline justify-between gap-x-2">
                          <span className="truncate text-textPrimary">{r.supplier_name}</span>
                          <span className={`shrink-0 font-medium ${r.risk_classification === "High" ? "text-danger" : r.risk_classification === "Medium" ? "text-warning" : "text-success"}`}>
                            {r.disruption_probability_pct}%
                          </span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <span className="mt-1 block text-[10px] text-textMuted">No supplier risk data</span>
                  )}
                </div>
                {/* Supply network graph — takes remaining space */}
                <div
                  className="glass-card flex min-h-0 flex-1 flex-col overflow-hidden p-3 font-mono transition hover:border-white/15"
                  role="button"
                  tabIndex={0}
                  onClick={() => setCalculationModal("operational-graph")}
                  onKeyDown={(e) => e.key === "Enter" && setCalculationModal("operational-graph")}
                >
                <div className="mb-3 flex shrink-0 items-center justify-between">
                  <span className="text-[11px] font-medium uppercase tracking-wide text-textMuted">
                    Supply network & impact propagation
                  </span>
                  <button
                    type="button"
                    onClick={(e) => { e.stopPropagation(); setCalculationModal("operational-graph"); }}
                    className="rounded p-1 text-textMuted hover:text-agentCyan focus:outline-none"
                    aria-label="How is this calculated?"
                  >
                    <InfoIcon className="h-4 w-4" />
                  </button>
                </div>
                {operationalImpact && operationalImpact.affectedProductionLines.length > 0 ? (
                  <div className="min-h-0 flex-1">
                    <OperationalImpactGraph
                      affectedProductionLines={operationalImpact.affectedProductionLines}
                      criticalDependencies={operationalImpact.criticalDependencies}
                      supplierNames={Object.fromEntries((data?.supplierRisks ?? []).map((r) => [r.supplier_id, r.supplier_name]))}
                      allSuppliers={data?.allSuppliers}
                    />
                  </div>
                ) : (
                  <span className="text-xs text-textMuted">No operational impact data</span>
                )}
              </div>
              </div>
            </section>
          </>
        ) : (
          <>
            {/* Map-only view: full-screen map with agent reasoning docked bottom-right */}
            <section className="relative flex-1 min-h-0 overflow-hidden">
              <div className="absolute inset-0">
                <GlobalDisruptionMap
                  disruptionRisk={kpis.disruptionRisk}
                  activeDisruptions={kpis.activeDisruptions}
                />
              </div>
              <div className="pointer-events-none absolute inset-0">
                <div className="pointer-events-auto absolute right-6 bottom-6 transition-all duration-300">
                  <div
                    className={`relative glass-card flex flex-col transition-all duration-300 ${
                      streamExpanded ? "w-[360px] max-h-[40vh]" : "w-[300px]"
                    }`}
                  >
                    <button
                      type="button"
                      onClick={() => setStreamExpanded((v) => !v)}
                      className="absolute top-1 left-1/2 z-10 -translate-x-1/2 text-slate-300 hover:text-agentCyan focus:outline-none focus:ring-0"
                    >
                      <svg
                        className="h-4 w-4"
                        viewBox="0 0 16 16"
                        fill="none"
                        xmlns="http://www.w3.org/2000/svg"
                      >
                        {streamExpanded ? (
                          // expanded: show down chevron
                          <path
                            d="M4 6L8 10L12 6"
                            stroke="currentColor"
                            strokeWidth="1.5"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          />
                        ) : (
                          // collapsed: show up chevron
                          <path
                            d="M4 10L8 6L12 10"
                            stroke="currentColor"
                            strokeWidth="1.5"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          />
                        )}
                      </svg>
                    </button>
                    <div className={`pt-5 ${streamExpanded ? "max-h-[40vh] overflow-y-auto" : ""}`}>
                      <AgentReasoningStream
                        entries={streamEntries}
                        showCursorLabel={true}
                        title=""
                        liveLabel={streamLoading ? "Loading…" : "Streaming"}
                        maxEntries={streamExpanded ? undefined : 1}
                      />
                    </div>
                  </div>
                </div>
              </div>
            </section>
          </>
        )}
      </div>

      {/* Calculation how-to modals */}
      <CalculationModal
        open={calculationModal === "supplier-risk"}
        onClose={() => setCalculationModal(null)}
        title="Supplier disruption probability (30d)"
      >
        <ul className="list-inside list-disc space-y-1.5 text-[11px]">
          <li>Per-supplier probability over a 30-day horizon using risk indicators.</li>
          <li>Indicators (0–1): delivery delay frequency (from disruption history), financial health risk (1 − health_score/100), region instability (geopolitical lift for Taiwan/Vietnam), logistics congestion (from active shipping lane status), weather (from climate alerts).</li>
          <li>Weighted combination: health 25%, region 25%, logistics 25%, delivery delay 15%, weather 10%.</li>
          <li>Uplifts: single-source supplier ×1.15; spend &gt;35% ×1.1. Result capped at 100%.</li>
          <li>Classification: Low &lt;35%, Medium 35–65%, High ≥65%. Primary drivers list the main contributing factors.</li>
        </ul>
      </CalculationModal>
      <CalculationModal
        open={calculationModal === "overall-risk"}
        onClose={() => setCalculationModal(null)}
        title="Overall Supply Risk"
      >
        <ul className="list-inside list-disc space-y-1.5 text-[11px]">
          <li>Aggregate supply risk for the whole network: the maximum of all per-supplier disruption probabilities.</li>
          <li>Each supplier’s probability uses the same model as “Supplier disruption probability (30d)” (weighted indicators + single-source and high-spend uplifts).</li>
          <li>The overall percentage is the highest supplier probability, so one high-risk supplier drives the overall number.</li>
        </ul>
      </CalculationModal>
      <CalculationModal
        open={calculationModal === "operational-impact"}
        onClose={() => setCalculationModal(null)}
        title="Operational Impact (production downtime probability)"
      >
        <ul className="list-inside list-disc space-y-1.5 text-[11px]">
          <li>Estimates how disruption propagates through the production network.</li>
          <li>Supply network: suppliers → components (inventory items) → production lines. Semiconductor items feed semiconductor-dependent lines; steel items feed other lines.</li>
          <li>Critical nodes: single-source suppliers and components with no substitutes.</li>
          <li>Monte Carlo simulation (300+ runs): each run samples a disruption length from active config (or 5–15 days). For lines that depend on single-source suppliers, we check if inventory (days_on_hand) runs out before the disruption ends.</li>
          <li>Production downtime % = fraction of runs where at least one production line stops. Estimated delay range = min–max of sampled disruption days.</li>
        </ul>
      </CalculationModal>
      <CalculationModal
        open={calculationModal === "operational-graph"}
        onClose={() => setCalculationModal(null)}
        title="Supply network & impact propagation graph"
      >
        <ul className="list-inside list-disc space-y-1.5 text-[11px]">
          <li>Nodes: Suppliers (left), Components / inventory items (center), Production lines (right).</li>
          <li>Edges: Material flows from supplier to component to line. Dashed red edges = single-source (critical) dependencies.</li>
          <li>Red-outlined production lines are at risk (depend on single-source components). Same logic as the Operational Impact percentage: if disruption lasts longer than inventory runway, that line stops.</li>
        </ul>
      </CalculationModal>
      <CalculationModal
        open={calculationModal === "revenue-at-risk"}
        onClose={() => setCalculationModal(null)}
        title="Revenue at Risk"
      >
        <ul className="list-inside list-disc space-y-1.5 text-[11px]">
          <li>Quantifies financial exposure from operational disruption using production lines and customer SLAs.</li>
          <li><strong>Lost production:</strong> For each at-risk production line, daily revenue × estimated delay days (from operational impact). Sum over all at-risk lines.</li>
          <li><strong>Revenue at risk</strong> = lost production (same formula). We report best case (min delay), expected (mid), and worst case (max delay).</li>
          <li><strong>Margin impact:</strong> Revenue at risk × margin rate (30%). Represents the hit to gross profit if disruption occurs.</li>
          <li><strong>SLA penalties:</strong> For each customer with a penalty_per_day in the profile, penalty × delay days. Included in total exposure.</li>
          <li><strong>Customers affected:</strong> Count of customer SLAs in the manufacturer profile (e.g. major OEM accounts).</li>
        </ul>
      </CalculationModal>
    </LayoutShell>
  );
}
