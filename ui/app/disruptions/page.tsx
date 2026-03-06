"use client";

import { useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { LayoutShell } from "../../components/LayoutShell";
import { AgentReasoningStream, type StreamEntry } from "../../components/AgentReasoningStream";

type DisruptionEvent = {
  id: string;
  impact: string;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  title: string;
  tags: string[];
  description: string;
  timeline: Array<{ time: string; text: string; muted?: boolean }>;
  source?: string;
  url?: string;
};

function FactoryIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor" aria-hidden>
      <path
        fillRule="evenodd"
        d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2h-1.535a2 2 0 01-1.528-1.118A2 2 0 0012.528 1H7.472a2 2 0 00-1.444.582A2 2 0 004.535 3H3zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm0 4a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function ChartBarsIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor" aria-hidden>
      <path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zM8 7a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zM14 4a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z" />
    </svg>
  );
}

function PlayIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor" aria-hidden>
      <path
        fillRule="evenodd"
        d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function ChevronRightIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor" aria-hidden>
      <path
        fillRule="evenodd"
        d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.06l-4.5 4.25a.75.75 0 01-1.06-.02z"
        clipRule="evenodd"
      />
    </svg>
  );
}

export default function DisruptionsPage() {
  const searchParams = useSearchParams();
  const idFromUrl = searchParams.get("id");

  const [events, setEvents] = useState<DisruptionEvent[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(idFromUrl);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [hasLoaded, setHasLoaded] = useState(false);
  const [traceEntries, setTraceEntries] = useState<StreamEntry[]>([]);
  const [traceLoading, setTraceLoading] = useState(false);
  const [bufferDays, setBufferDays] = useState(14);
  const [scenarioResult, setScenarioResult] = useState<{
    rankedScenarios: Array<{
      scenarioName: string;
      incrementalCostUsd?: number;
      implementationDays?: number;
      serviceLevelProtection?: string;
      adjustedScore?: number;
    }>;
    topRecommendation: {
      scenarioName: string;
      incrementalCostUsd?: number;
      implementationDays?: number;
      serviceLevelProtection?: string;
    } | null;
  } | null>(null);
  const [scenarioLoading, setScenarioLoading] = useState(false);
  const [scenarioError, setScenarioError] = useState<string | null>(null);

  useEffect(() => {
    setHasLoaded(false);
    fetch("/api/disruptions")
      .then((res) => {
        if (!res.ok) throw new Error("Failed to load disruptions");
        return res.json();
      })
      .then((data: DisruptionEvent[]) => {
        setEvents(data);
        if (data.length > 0) {
          const idToSelect = idFromUrl && data.some((e) => e.id === idFromUrl)
            ? idFromUrl
            : data[0].id;
          setSelectedId(idToSelect);
        }
        setHasLoaded(true);
      })
      .catch((e) => {
        setLoadError(e instanceof Error ? e.message : "Failed to load");
        setHasLoaded(true);
      });
  }, [idFromUrl]);

  useEffect(() => {
    const params = new URLSearchParams({ context: "disruption" });
    if (selectedId) params.set("eventId", selectedId);
    const fetchTrace = () => {
      fetch(`/api/agent-stream?${params}`)
        .then((res) => {
          if (!res.ok) throw new Error("Failed to load trace");
          return res.json();
        })
        .then((entries: StreamEntry[]) => setTraceEntries(Array.isArray(entries) ? entries : []))
        .catch(() => setTraceEntries([]))
        .finally(() => setTraceLoading(false));
    };
    setTraceLoading(true);
    fetchTrace();
    const interval = setInterval(fetchTrace, 2500);
    return () => clearInterval(interval);
  }, [selectedId]);

  const selected = selectedId ? events.find((e) => e.id === selectedId) ?? events[0] : events[0];

  const runScenario = () => {
    if (!selected) return;
    setScenarioError(null);
    setScenarioResult(null);
    setScenarioLoading(true);
    fetch("/api/scenarios/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        eventId: selected.id,
        bufferDays,
        riskAppetite: "low",
      }),
    })
      .then((res) => {
        if (!res.ok) throw new Error("Scenario run failed");
        return res.json();
      })
      .then((data) => {
        setScenarioResult({
          rankedScenarios: data.rankedScenarios ?? [],
          topRecommendation: data.topRecommendation ?? null,
        });
      })
      .catch((e) => setScenarioError(e instanceof Error ? e.message : "Failed to run scenario"))
      .finally(() => setScenarioLoading(false));
  };

  return (
    <LayoutShell
      title="Disruption Workspace"
      subtitle="Deep-dive with agent reasoning trace & what-if scenario modeling."
    >
      <div className="flex h-full min-h-0 gap-4">
        {/* Left: Active disruptions list — scrollable */}
        <section className="flex min-h-0 w-[280px] shrink-0 flex-col">
          <h2 className="mb-3 shrink-0 text-xs font-semibold text-textPrimary">
            Active Disruptions
          </h2>
          <div className="min-h-0 flex-1 space-y-2 overflow-y-auto">
            {loadError && (
              <p className="text-xs text-danger">{loadError}</p>
            )}
            {!hasLoaded && !loadError && (
              <p className="text-xs text-textMuted">Loading…</p>
            )}
            {hasLoaded && events.length === 0 && !loadError && (
              <p className="text-xs text-textMuted">No active disruptions. Toggle active in config/active_disruption.json to show events.</p>
            )}
            {events.map((event) => {
              const isSelected = event.id === selected.id;
              return (
                <button
                  key={event.id}
                  onClick={() => setSelectedId(event.id)}
                  className={`flex w-full items-center gap-2 rounded-lg border px-3 py-2.5 text-left transition ${
                    isSelected
                      ? "border-accent/50 bg-surfaceMuted"
                      : "border-white/5 bg-surface/80 hover:border-white/10"
                  }`}
                >
                  <div className="min-w-0 flex-1">
                    <div className="mb-1 flex items-center justify-between gap-2 text-[11px]">
                      <span
                        className={
                          event.severity === "CRITICAL"
                            ? "pill-critical"
                            : event.severity === "HIGH"
                              ? "pill-high"
                              : event.severity === "MEDIUM"
                                ? "pill-medium-severity"
                                : "pill-low"
                        }
                      >
                        {event.severity}
                      </span>
                      <span className="font-mono text-textMuted">{event.id}</span>
                    </div>
                    <p className="truncate text-xs font-medium text-textPrimary">
                      {event.title}
                    </p>
                  </div>
                  <ChevronRightIcon className="h-4 w-4 shrink-0 text-textMuted" />
                </button>
              );
            })}
          </div>
        </section>

        {/* Right: Detail, timeline, what-if, agent trace */}
        <section className="flex min-h-0 flex-1 flex-col gap-4 overflow-hidden">
            {!selected ? (
              <div className="glass-card p-4 text-textMuted text-sm">
                {events.length === 0
                  ? "No disruptions found. Configure GOOGLE_SEARCH_API_KEY and GOOGLE_SEARCH_ENGINE_ID in .env.local for real-world signals, or set active to true in config/active_disruption.json for mock events."
                  : "Select a disruption."}
              </div>
            ) : (
          <>
          {/* Disruption header */}
          <div className="shrink-0">
            <div className="glass-card p-4">
            <div className="mb-2 flex items-start justify-between gap-4">
              <div className="flex items-start gap-2">
                <FactoryIcon className="mt-0.5 h-5 w-5 shrink-0 text-accent" />
                <div>
                  <div className="font-mono text-base font-semibold tracking-tight text-textPrimary">
                    {selected.id}
                  </div>
                  <p className="mt-1 text-sm text-textPrimary">
                    {selected.description}
                  </p>
                  {selected.source && (
                    <span className="mt-1 block text-[10px] text-textMuted">
                      Source: {selected.source}
                    </span>
                  )}
                </div>
              </div>
              <div className="shrink-0 text-right text-[11px]">
                <span className="font-mono font-semibold text-danger">
                  Impact: {selected.impact}
                </span>
                {selected.url && (
                  <a
                    href={selected.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-2 block text-agentCyan hover:underline"
                  >
                    Open article →
                  </a>
                )}
              </div>
            </div>
            <div className="mt-3 flex flex-wrap gap-1.5">
              {selected.tags.map((t) => (
                <span
                  key={t}
                  className="font-mono rounded-md bg-surfaceMuted px-2 py-1 text-[10px] text-textPrimary"
                >
                  {t}
                </span>
              ))}
            </div>
          </div>
          </div>

          <div className="grid min-h-0 flex-1 grid-cols-12 gap-4 overflow-hidden">
            {/* Event timeline */}
            <div className="col-span-5 shrink-0">
              <div className="glass-card h-full p-4">
              <h3 className="mb-3 font-mono text-[11px] font-semibold uppercase tracking-wide text-textMuted">
                Event Timeline
              </h3>
              <ol className="space-y-2 text-[11px]">
                {selected.timeline.map((item, i) => (
                  <li key={i} className="flex flex-col gap-0.5">
                    <span className="shrink-0 font-mono text-agentCyan text-[10px]">
                      {item.time}
                    </span>
                    <span
                      className={
                        item.muted ? "text-textMuted" : "text-textPrimary"
                      }
                    >
                      {item.text}
                    </span>
                  </li>
                ))}
              </ol>
              </div>
            </div>

            {/* What-If + Agent Reasoning Trace */}
            <div className="col-span-7 flex min-h-0 flex-col gap-4 overflow-hidden">
              {/* What-If Scenario */}
              <div className="shrink-0">
                <div className="glass-card p-4">
                <div className="mb-2 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <ChartBarsIcon className="h-4 w-4 text-textMuted" />
                    <span className="text-xs font-semibold">
                      What-If Scenario
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={runScenario}
                    disabled={scenarioLoading || !selected}
                    className="flex items-center gap-1.5 rounded-md border border-agentCyan/50 bg-agentCyan/10 px-3 py-1.5 font-mono text-[11px] text-agentCyan disabled:opacity-50"
                  >
                    <PlayIcon className="h-3.5 w-3.5" />
                    {scenarioLoading ? "Running…" : "Run Scenario"}
                  </button>
                </div>
                <div className="text-[11px] text-textMuted">
                  Safety Stock Buffer (days)
                </div>
                <div className="mt-2 flex items-center gap-3">
                    <input
                    type="range"
                    min={5}
                    max={60}
                    value={bufferDays}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                      setBufferDays(Number(e.target.value))
                    }
                    className="h-1.5 flex-1 appearance-none rounded-md bg-surfaceMuted accent-agentCyan"
                  />
                  <span className="font-mono text-sm font-semibold text-textPrimary w-8">
                    {bufferDays}
                  </span>
                </div>
                {scenarioError && (
                  <p className="mt-3 text-[11px] text-danger">{scenarioError}</p>
                )}
                {scenarioResult && !scenarioError && (
                  <div className="mt-3 space-y-2 border-t border-white/5 pt-3">
                    {scenarioResult.topRecommendation && (
                      <div className="rounded-md border border-agentCyan/30 bg-agentCyan/5 px-3 py-2">
                        <div className="text-[10px] font-medium uppercase tracking-wide text-agentCyan">
                          Top recommendation
                        </div>
                        <div className="mt-1 font-mono text-xs font-semibold text-textPrimary">
                          {scenarioResult.topRecommendation.scenarioName}
                        </div>
                        <div className="mt-0.5 text-[11px] text-textMuted">
                          {scenarioResult.topRecommendation.incrementalCostUsd != null &&
                            `$${scenarioResult.topRecommendation.incrementalCostUsd.toLocaleString()} · `}
                          {scenarioResult.topRecommendation.implementationDays != null &&
                            `${scenarioResult.topRecommendation.implementationDays}d · `}
                          {scenarioResult.topRecommendation.serviceLevelProtection ?? ""} SLA
                        </div>
                      </div>
                    )}
                    <div className="text-[10px] font-medium uppercase tracking-wide text-textMuted">
                      All scenarios
                    </div>
                    <ul className="space-y-1.5 text-[11px]">
                      {scenarioResult.rankedScenarios.map((s, i) => (
                        <li key={i} className="flex justify-between gap-2">
                          <span className="text-textPrimary">
                            {i + 1}. {s.scenarioName}
                          </span>
                          <span className="font-mono text-textMuted shrink-0">
                            {s.incrementalCostUsd != null
                              ? `$${s.incrementalCostUsd.toLocaleString()}`
                              : "—"}{" "}
                            · {s.implementationDays ?? "?"}d
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                </div>
              </div>

              {/* Agent Reasoning Trace — scrollable */}
              <div className="glass-card flex min-h-0 flex-1 flex-col overflow-hidden p-4">
                <AgentReasoningStream
                  entries={traceEntries}
                  showCursorLabel={true}
                  title="Agent Reasoning Trace"
                  liveLabel={traceLoading ? "Loading…" : "Live"}
                />
              </div>
              </div>
            </div>
          </>
          )}
        </section>
      </div>
    </LayoutShell>
  );
}
