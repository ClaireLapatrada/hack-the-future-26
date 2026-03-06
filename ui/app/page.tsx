"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { LayoutShell } from "../components/LayoutShell";
import { AgentReasoningStream, type StreamEntry } from "../components/AgentReasoningStream";
import { GlobalDisruptionMap } from "../components/GlobalDisruptionMap";

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
};

function ShieldIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor" aria-hidden>
      <path
        fillRule="evenodd"
        d="M10 1.944A11.954 11.954 0 012.166 5C2.056 5.649 2 6.319 2 7c0 5.225 3.34 9.67 8 11.317C14.66 16.67 18 12.225 18 7c0-.682-.057-1.35-.166-2.001A11.954 11.954 0 0110 1.944zM11 14a1 1 0 11-2 0 1 1 0 012 0zm0-7a1 1 0 10-2 0 1 1 0 002 0z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function DollarIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor" aria-hidden>
      <path d="M8.433 7.418c.155-.103.346-.196.567-.267v1.698a2.305 2.305 0 01-.567-.267C8.07 8.34 8 8.114 8 8c0-.114.07-.34.433-.582zM11 12.849v-1.698c.22.071.412.164.567.267.364.243.433.468.433.582 0 .114-.07.34-.433.582a2.305 2.305 0 01-.567.267z" />
      <path
        fillRule="evenodd"
        d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-13a1 1 0 10-2 0v.092a4.535 4.535 0 00-1.676.662C6.602 6.234 6 7.009 6 8c0 .99.602 1.765 1.324 2.246.48.32 1.054.545 1.676.662v1.941c-.391-.127-.68-.317-.843-.504a1 1 0 10-1.411 1.41c.82.823 1.977 1.243 3.254 1.243 1.277 0 2.434-.42 3.253-1.244a1 1 0 00-1.412-1.416c-.163.187-.452.377-.843.504v-1.94a4.535 4.535 0 001.676-.662C13.398 9.766 14 8.991 14 8c0-.99-.602-1.765-1.324-2.246A4.535 4.535 0 0011 5.092V4z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function CubeIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor" aria-hidden>
      <path d="M11 17a1 1 0 001.447.894l4-2A1 1 0 0017 15V9.236a1 1 0 00-1.447-.894l-4 2a1 1 0 00-.553.894V17zM15.211 6.276a1 1 0 000-1.788l-4-2a1 1 0 00-.894 0l-4 2a1 1 0 000 1.788l4 2a1 1 0 00.894 0l4-2zM4.553 7.894a1 1 0 001.447.894V15a1 1 0 00.553.894l4 2A1 1 0 0011 17v-5.764a1 1 0 00-.553-.894l-4-2z" />
    </svg>
  );
}

function ChartWaveIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor" aria-hidden>
      <path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zM8 7a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zM14 4a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z" />
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
      <div className="flex h-full min-h-0 flex-col gap-4 overflow-hidden">
        {viewMode === "dashboard" ? (
          <>
            {/* KPI row */}
            <section className="grid shrink-0 grid-cols-4 gap-4">
              <div className="glass-card relative flex flex-col gap-1 p-4 font-mono">
                <div className="absolute right-4 top-4">
                  <ShieldIcon className="h-5 w-5 text-danger" />
                </div>
                <span className="text-[11px] font-medium uppercase tracking-wide text-textMuted">
                  Disruption Risk
                </span>
                <span className="text-2xl font-semibold">{kpis.disruptionRisk}</span>
                <span className="text-xs text-danger">{trendLabel(kpis.disruptionRiskTrendPct ?? 0)}</span>
              </div>
              <div className="glass-card relative flex flex-col gap-1 p-4 font-mono">
                <div className="absolute right-4 top-4">
                  <DollarIcon className="h-5 w-5 text-textPrimary" />
                </div>
                <span className="text-[11px] font-medium uppercase tracking-wide text-textMuted">
                  Revenue at Risk
                </span>
                <span className="text-2xl font-semibold">{revenueStr}</span>
                <span className="text-xs text-danger">{trendLabel(kpis.revenueTrendPct ?? 0)}</span>
              </div>
              <div className="glass-card relative flex flex-col gap-1 p-4 font-mono">
                <div className="absolute right-4 top-4">
                  <CubeIcon className="h-5 w-5 text-agentCyan" />
                </div>
                <span className="text-[11px] font-medium uppercase tracking-wide text-textMuted">
                  Active Disruptions
                </span>
                <span className="text-2xl font-semibold">{kpis.activeDisruptions}</span>
                <span className="text-xs text-success">{trendLabel(kpis.activeDisruptionsTrendPct ?? 0)}</span>
              </div>
              <div className="glass-card relative flex flex-col gap-1 p-4 font-mono">
                <div className="absolute right-4 top-4">
                  <ChartWaveIcon className="h-5 w-5 text-agentCyan" />
                </div>
                <span className="text-[11px] font-medium uppercase tracking-wide text-textMuted">
                  Pending Approvals
                </span>
                <span className="text-2xl font-semibold">{kpis.pendingApprovals}</span>
                <span className="text-xs text-textMuted">{trendLabel(kpis.pendingApprovalsTrendPct ?? 0)}</span>
              </div>
            </section>

            {/* Risk pills row */}
            <section className="shrink-0">
              <div className="flex gap-4">
                {(() => {
                  const t1 = riskTier(kpis.overallSupplyRisk);
                  return (
                    <div className={`flex flex-1 flex-col justify-center gap-2 rounded-lg border ${t1.border} ${t1.bg} px-4 py-3 font-mono text-xs transition-colors duration-300`}>
                      <span className={`font-medium ${t1.text}`}>Overall Supply Risk</span>
                      <span className={`text-2xl font-semibold ${t1.text} transition-colors duration-300`}>{kpis.overallSupplyRisk}</span>
                      <div className={`h-1.5 rounded-md ${t1.barBg}`}>
                        <div
                          className={`risk-pill-bar-fill h-full rounded-md ${t1.barFill}`}
                          style={{ width: `${Math.min(100, kpis.overallSupplyRisk)}%` }}
                        />
                      </div>
                    </div>
                  );
                })()}
                {(() => {
                  const t2 = riskTier(kpis.logisticsFreight);
                  return (
                    <div className={`flex flex-1 flex-col justify-center gap-2 rounded-lg border ${t2.border} ${t2.bg} px-4 py-3 font-mono text-xs transition-colors duration-300`}>
                      <span className={`font-medium ${t2.text}`}>Logistics & Freight</span>
                      <span className={`text-2xl font-semibold ${t2.text} transition-colors duration-300`}>{kpis.logisticsFreight}</span>
                      <div className={`h-1.5 rounded-md ${t2.barBg}`}>
                        <div
                          className={`risk-pill-bar-fill h-full rounded-md ${t2.barFill}`}
                          style={{ width: `${Math.min(100, kpis.logisticsFreight)}%` }}
                        />
                      </div>
                    </div>
                  );
                })()}
                {(() => {
                  const t3 = riskTier(kpis.supplierConcentration);
                  return (
                    <div className={`flex flex-1 flex-col justify-center gap-2 rounded-lg border ${t3.border} ${t3.bg} px-4 py-3 font-mono text-xs transition-colors duration-300`}>
                      <span className={`font-medium ${t3.text}`}>Supplier Concentration</span>
                      <span className={`text-2xl font-semibold ${t3.text} transition-colors duration-300`}>{kpis.supplierConcentration}</span>
                      <div className={`h-1.5 rounded-md ${t3.barBg}`}>
                        <div
                          className={`risk-pill-bar-fill h-full rounded-md ${t3.barFill}`}
                          style={{ width: `${Math.min(100, kpis.supplierConcentration)}%` }}
                        />
                      </div>
                    </div>
                  );
                })()}
              </div>
            </section>

            {/* Bottom row: Active Disruptions + Agent reasoning */}
            <section className="grid min-h-0 flex-1 grid-cols-2 gap-4">
              <div className="glass-card flex min-h-0 flex-col overflow-hidden p-4">
                <div className="mb-3 flex shrink-0 items-center justify-between text-xs">
                  <span className="font-semibold">Active Disruptions</span>
                  <span className="flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-wide text-success">
                    <span className="h-1.5 w-1.5 rounded-md bg-success" />
                    Live
                  </span>
                </div>
                <div className="min-h-0 flex-1 overflow-y-auto">
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

              <div className="glass-card flex min-h-0 flex-col overflow-hidden p-4">
                <AgentReasoningStream
                  entries={streamEntries}
                  showCursorLabel={true}
                  title="Agent Reasoning Stream"
                  liveLabel={streamLoading ? "Loading…" : "Streaming"}
                />
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
    </LayoutShell>
  );
}
