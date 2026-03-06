"use client";

import { useRef, useEffect, useState } from "react";
import Link from "next/link";

const REVEAL_DELAY_MS = 500;

export type StreamEntryType = "OBSERVE" | "ACTION" | "RESULT" | "REASON" | "REASONING" | "PLANNING" | "MEMORY" | "TOOL";

export type StreamEntry = {
  type: StreamEntryType;
  time: string;
  content: string;
  confidence?: string;
  /** PO adjustment, escalation, or workflow integration (one-stop mitigation) */
  category?: "po_adjustment" | "escalation" | "workflow_integration";
  /** When present, show "View document" link to planning document */
  meta?: { documentId?: string };
  /** Optional detailed view: pretty-printed tool result or calculation breakdown */
  detail?: string;
};

function AgentReasoningIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 16 16" fill="currentColor" aria-hidden>
      <ellipse cx="8" cy="10" rx="4" ry="3" />
      <rect x="6" y="4" width="4" height="4" rx="1" />
      <circle cx="7" cy="6.5" r="0.6" />
      <circle cx="9" cy="6.5" r="0.6" />
      <path d="M8 2 L8 0 M5.5 1.5 L4.5 0.5 M10.5 1.5 L11.5 0.5" stroke="currentColor" strokeWidth="0.8" fill="none" />
    </svg>
  );
}

function StreamEyeIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor" aria-hidden>
      <path d="M10 12a2 2 0 100-4 2 2 0 000 4z" />
      <path fillRule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clipRule="evenodd" />
    </svg>
  );
}
function StreamLightningIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor" aria-hidden>
      <path fillRule="evenodd" d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z" clipRule="evenodd" />
    </svg>
  );
}
function StreamResultIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor" aria-hidden>
      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
    </svg>
  );
}
function StreamReasonIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor" aria-hidden>
      <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
    </svg>
  );
}
function StreamToolIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor" aria-hidden>
      <path fillRule="evenodd" d="M12.316 3.051a1 1 0 01.633 1.265l-4 12a1 1 0 11-1.898-.632l4-12a1 1 0 011.265-.633z" clipRule="evenodd" />
      <path fillRule="evenodd" d="M4.5 4.5A1.5 1.5 0 006 6v8a1.5 1.5 0 01-3 0V6a1.5 1.5 0 011.5-1.5zm9 0A1.5 1.5 0 0115 6v8a1.5 1.5 0 01-3 0V6a1.5 1.5 0 011.5-1.5z" clipRule="evenodd" />
    </svg>
  );
}
function StreamPlanningIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor" aria-hidden>
      <path fillRule="evenodd" d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zm0 6a1 1 0 011-1h6a1 1 0 011 1v4a1 1 0 01-1 1H4a1 1 0 01-1-1v-4zm8 0a1 1 0 011-1h6a1 1 0 011 1v4a1 1 0 01-1 1h-6a1 1 0 01-1-1v-4z" clipRule="evenodd" />
    </svg>
  );
}
function StreamMemoryIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor" aria-hidden>
      <path d="M3 12v3c0 1.657 3.134 3 7 3s7-1.343 7-3v-3c0 1.657-3.134 3-7 3s-7-1.343-7-3z" />
      <path d="M3 7v3c0 1.657 3.134 3 7 3s7-1.343 7-3V7c0 1.657-3.134 3-7 3S3 8.657 3 7z" />
      <path d="M17 5c0 1.657-3.134 3-7 3S3 6.657 3 5s3.134-3 7-3 7 1.343 7 3z" />
    </svg>
  );
}

const STREAM_TYPE_CONFIG = {
  OBSERVE: { Icon: StreamEyeIcon, colorClass: "text-agentCyan", label: "OBSERVE" },
  ACTION: { Icon: StreamLightningIcon, colorClass: "text-danger", label: "ACTION" },
  RESULT: { Icon: StreamResultIcon, colorClass: "text-success", label: "RESULT" },
  REASON: { Icon: StreamReasonIcon, colorClass: "text-accent", label: "REASON" },
  REASONING: { Icon: StreamReasonIcon, colorClass: "text-accent", label: "REASONING" },
  PLANNING: { Icon: StreamPlanningIcon, colorClass: "text-warning", label: "PLANNING" },
  MEMORY: { Icon: StreamMemoryIcon, colorClass: "text-textMuted", label: "MEMORY" },
  TOOL: { Icon: StreamToolIcon, colorClass: "text-textMuted", label: "TOOL" },
} as const;

/** Category labels for PO adjustment, escalation, workflow integration (one-stop mitigation) */
const STREAM_CATEGORY_LABELS: Record<string, { label: string; title: string }> = {
  po_adjustment: {
    label: "PO / Restock",
    title: "Purchase order adjustment: monitor inventory, suggest restocks, execute after approval; small restocks can auto-execute.",
  },
  escalation: {
    label: "Escalation",
    title: "Automatically escalate to higher management; see Decision transparency.",
  },
  workflow_integration: {
    label: "Workflow",
    title: "One-stop mitigation: client software, company stance, sustainability, financial, legal, SCM inputs.",
  },
};

const TOOL_LIKE_TYPES = ["TOOL", "OBSERVE", "REASONING", "PLANNING", "ACTION", "MEMORY"] as const;

/** Simple typewriter effect for a single line of text. */
function useTypewriter(text: string, enabled: boolean, speedMs: number = 18): string {
  const [display, setDisplay] = useState<string>(enabled ? "" : text);

  useEffect(() => {
    if (!enabled) {
      setDisplay(text);
      return;
    }
    setDisplay("");
    let i = 0;
    const id = setInterval(() => {
      i += 1;
      setDisplay(text.slice(0, i));
      if (i >= text.length) {
        clearInterval(id);
      }
    }, speedMs);
    return () => clearInterval(id);
  }, [text, enabled, speedMs]);

  return display;
}

/** Collapse tool-domain + RESULT pairs into one entry with resultStatus and detail; drop standalone RESULTs. */
type DisplayEntry = StreamEntry & { resultStatus?: "success" | "error" | string };

function collapseToolResultPairs(entries: StreamEntry[]): DisplayEntry[] {
  const out: DisplayEntry[] = [];
  for (let i = 0; i < entries.length; i++) {
    const e = entries[i];
    const raw = e.content?.trim() ?? "";
    // Only treat as tool-call if type is tool-domain AND content looks like tools.module.fn(...)
    const isToolLike =
      TOOL_LIKE_TYPES.some((t) => t === e.type) && /^tools\.\w+\.\w+\(/.test(raw);
    if (isToolLike) {
      const next = entries[i + 1];
      if (next?.type === "RESULT") {
        const r = next.content.trim().toLowerCase();
        out.push({
          ...e,
          resultStatus:
            r === "success" ? "success" : r === "error" ? "error" : next.content.trim(),
          ...(next.meta && typeof next.meta === "object" && { meta: next.meta }),
          ...(typeof (next as any).detail === "string" && { detail: (next as any).detail }),
        });
        i++;
      } else {
        out.push(e);
      }
    } else if (e.type === "RESULT") {
      continue;
    } else {
      out.push(e);
    }
  }
  return out;
}

/** Turn tool-call and other content into short human-readable sentences. */
function formatStreamContent(entry: StreamEntry): string {
  const raw = entry.content.trim();
  const type = entry.type;

  if (TOOL_LIKE_TYPES.includes(type as (typeof TOOL_LIKE_TYPES)[number]) && raw.match(/^tools\.\w+\.\w+\(/)) {
    const match = raw.match(/tools\.\w+\.(\w+)\((.*)\)\s*$/s);
    if (!match) return raw;
    const fn = match[1];
    const argsStr = match[2];
    const arg = (key: string): string | undefined => {
      const re = new RegExp(`${key}\\s*=\\s*'([^']*)'|${key}\\s*=\\s*"([^"]*)"|${key}\\s*=\\s*\\[([^\\]]*)\\]`);
      const m = argsStr.match(re);
      if (!m) return undefined;
      if (m[1] !== undefined) return m[1];
      if (m[2] !== undefined) return m[2];
      if (m[3] !== undefined) return m[3].replace(/'/g, "").trim();
      return undefined;
    };
    const num = (key: string): number | undefined => {
      const m = argsStr.match(new RegExp(`${key}\\s*=\\s*(\\d+)`));
      return m ? parseInt(m[1], 10) : undefined;
    };

    switch (fn) {
      case "search_disruption_news":
        return `Searching disruption news for "${arg("query") ?? "topic"}".`;
      case "get_shipping_lane_status":
        return `Checking shipping lane status for ${arg("lane") ?? "lane"}.`;
      case "get_climate_alerts":
        return `Fetching climate alerts for ${arg("regions")?.replace(/,/g, ", ") ?? "selected regions"}.`;
      case "score_supplier_health":
        return `Checking supplier health score for ${arg("supplier_id") ?? "supplier"}.`;
      case "retrieve_similar_disruptions":
        return `Looking up similar past disruptions (${arg("disruption_type") ?? "type"}, ${arg("affected_region") ?? "region"}).`;
      case "get_supplier_exposure":
        return `Getting supplier exposure for ${arg("supplier_id") ?? "supplier"}.`;
      case "get_inventory_runway":
        return `Checking inventory runway for ${arg("item_id") ?? "item"}.`;
      case "calculate_revenue_at_risk":
        return `Calculating revenue at risk for ${arg("affected_supplier_id") ?? "supplier"} (${num("estimated_delay_days") ?? "?"} days delay).`;
      case "calculate_sla_breach_probability":
        return `Calculating SLA breach probability for ${arg("customer_name") ?? "customer"}.`;
      case "simulate_mitigation_scenario":
        return `Simulating ${arg("scenario_type")?.replace(/_/g, " ") ?? "mitigation"} scenario for ${arg("affected_item_id") ?? "item"} (${num("disruption_days") ?? "?"} days, ${num("quantity_needed") ?? "?"} units).`;
      case "get_alternative_suppliers":
        return `Fetching alternative ${arg("category") ?? "suppliers"}${arg("exclude_regions") ? ` (excluding ${arg("exclude_regions")})` : ""}.`;
      case "rank_scenarios":
        return "Ranking mitigation scenarios by risk appetite.";
      case "run_scenario_simulation":
        return `Running scenario simulation (${num("monte_carlo_runs") ?? "?"} runs, risk appetite: ${arg("risk_appetite") ?? "medium"}).`;
      case "optimize_supplier_reallocation":
        return `Optimizing supplier reallocation${arg("demand_units") ? ` (${arg("demand_units")} units)` : ""}.`;
      case "recommend_buffer_stock":
        return `Recommending buffer stock for ${arg("item_id") ?? "item"} (service level: ${arg("service_level_target_pct") ?? "95"}%).`;
      case "send_slack_alert":
        return `Sending Slack alert to ${arg("channel") ?? "channel"} (${arg("severity") ?? "alert"}).`;
      case "draft_supplier_email":
        return `Drafting email to ${arg("supplier_name") ?? "supplier"}.`;
      case "flag_erp_reorder_adjustment":
        return `Flagging ERP adjustment for ${arg("item_id") ?? "item"} (${arg("adjustment_type")?.replace(/_/g, " ") ?? "update"}).`;
      case "generate_executive_summary":
        return "Generating executive summary.";
      case "submit_mitigation_for_approval":
        return `Submitting mitigation for approval: ${arg("title") ?? "recommendation"}.`;
      case "get_po_adjustment_suggestions":
        return "Checking inventory and suggesting restock orders (PO adjustments).";
      case "submit_restock_for_approval":
        return `Submitting restock for approval: ${arg("item_id") ?? "item"} (${num("suggested_quantity") ?? "?"} units).`;
      case "execute_approved_restock":
        return `Executing approved restock (${arg("approval_id") ?? "approval"}).`;
      case "escalate_to_management":
        return `Escalating to management: ${arg("trigger_reason") ?? "trigger"} (${arg("severity") ?? "severity"}).`;
      case "get_client_context":
        return "Loading client context (stance, sustainability, financial, legal, SCM).";
      case "get_workflow_integration_status":
        return "Checking workflow integrations (ERP, Slack, email, WMS, TMS).";
      case "create_planning_document":
        return `Creating planning document: ${arg("title") ?? "Mitigation plan"}.`;
      case "log_disruption_event":
        return `Logging disruption event (${arg("region") ?? "region"}, ${arg("severity") ?? "severity"}).`;
      default:
        const readable = fn.replace(/_/g, " ");
        return `Running ${readable}.`;
    }
  }

  if (type === "OBSERVE" || type === "ACTION" || type === "REASON") {
    if (raw.length > 0 && !raw.endsWith(".") && !raw.endsWith("!") && !raw.endsWith("?"))
      return raw + ".";
    return raw;
  }

  return raw;
}

function resultStatusLabel(status: "success" | "error" | string): { text: string; className: string } {
  if (status === "success") return { text: "Success", className: "text-success" };
  if (status === "error") return { text: "Failed", className: "text-danger" };
  return { text: status, className: "text-textMuted" };
}

export function AgentReasoningStream({
  entries,
  showCursorLabel = false,
  title,
  liveLabel,
  maxEntries,
}: {
  entries: StreamEntry[];
  showCursorLabel?: boolean;
  title?: string;
  liveLabel?: string;
  maxEntries?: number;
}) {
  // API returns newest-first. For correct TOOL+RESULT pairing, collapse on chronological order,
  // then reverse back to newest-first for display.
  const chronological = [...entries].reverse();
  const collapsedChronological = collapseToolResultPairs(chronological);
  const collapsed = collapsedChronological.reverse();
  // Keep newest at top, oldest at bottom
  const fullList =
    typeof maxEntries === "number" && maxEntries > 0
      ? collapsed.slice(0, maxEntries)
      : collapsed;

  const newestEntry = fullList[0];
  const newestFormatted = newestEntry ? formatStreamContent(newestEntry) : "";
  const typewriterText = useTypewriter(newestFormatted, !!newestEntry);

  const [revealCount, setRevealCount] = useState(0);
  const prevLengthRef = useRef(0);

  useEffect(() => {
    if (fullList.length === 0) {
      setRevealCount(0);
      prevLengthRef.current = 0;
      return;
    }
    if (fullList.length < prevLengthRef.current) {
      setRevealCount((c) => Math.min(c, fullList.length));
    }
    prevLengthRef.current = fullList.length;
  }, [fullList.length]);

  useEffect(() => {
    if (revealCount >= fullList.length) return;
    const t = setTimeout(() => {
      setRevealCount((c) => Math.min(c + 1, fullList.length));
    }, REVEAL_DELAY_MS);
    return () => clearTimeout(t);
  }, [revealCount, fullList.length]);

  const visibleEntries = fullList.slice(0, revealCount);

  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);

  /** Show approval link inside the TOOL entry that submitted for approval, not at top. */
  function isApprovalSubmission(entry: StreamEntry): boolean {
    if (entry.type !== "TOOL" && entry.type !== "ACTION") return false;
    return (
      entry.content.includes("submit_mitigation_for_approval") ||
      entry.content.includes("submit_restock_for_approval")
    );
  }

  return (
    <div className="flex h-full min-h-0 flex-1 flex-col overflow-hidden">
      <div className="min-h-0 flex-1 space-y-2 overflow-y-auto overflow-x-hidden p-2">
        {visibleEntries.map((entry, i) => {
          const config = STREAM_TYPE_CONFIG[entry.type as keyof typeof STREAM_TYPE_CONFIG] ?? STREAM_TYPE_CONFIG.TOOL;
          const Icon = config.Icon;
          const displayEntry = entry as DisplayEntry;
          const status = displayEntry.resultStatus;
          const statusDisplay = status ? resultStatusLabel(status) : null;
          const isNew = i === 0;
          const showApprovalInEntry = isApprovalSubmission(entry);
          const hasDetail = typeof displayEntry.detail === "string" && displayEntry.detail.length > 0;
          const isDetailExpanded = expandedIndex === i;
          const formatted = formatStreamContent(entry);
          const textToShow = isNew && !hasDetail ? typewriterText : formatted;
          return (
            <div
              key={`stream-${i}`}
              className={`rounded-lg border border-white/5 bg-surfaceMuted px-3 py-2.5 font-mono ${
                isNew ? "stream-entry-new animate-glow" : "stream-entry-old"
              }`}
            >
              <div className="mb-1 flex flex-col gap-0.5 text-[11px]">
                <div className="flex items-center gap-2 flex-wrap">
                  <Icon className={`h-4 w-4 shrink-0 ${config.colorClass}`} />
                  <span className={`font-medium uppercase ${config.colorClass}`}>
                    {config.label}
                  </span>
                  {"category" in entry && entry.category && STREAM_CATEGORY_LABELS[entry.category] && (
                    <span
                      className="rounded px-1.5 py-0.5 text-[9px] font-medium uppercase bg-white/10 text-textMuted"
                      title={STREAM_CATEGORY_LABELS[entry.category].title}
                    >
                      {STREAM_CATEGORY_LABELS[entry.category].label}
                    </span>
                  )}
                  {statusDisplay && (
                    <span className={`ml-1 text-[10px] ${statusDisplay.className}`}>
                      — {statusDisplay.text}
                    </span>
                  )}
                  {"confidence" in entry && entry.confidence != null && (
                    <span className="text-textMuted">conf: {entry.confidence}</span>
                  )}
                </div>
                <span className="text-[10px] text-textMuted">{entry.time}</span>
              </div>
              <p className="text-[11px] text-textPrimary">
                {textToShow}
              </p>
              {hasDetail && (
                <div className="mt-2">
                  <button
                    type="button"
                    onClick={() => setExpandedIndex(isDetailExpanded ? null : i)}
                    className="text-[10px] font-mono text-agentCyan hover:text-agentCyan/80"
                  >
                    {isDetailExpanded ? "Hide details" : "Show details"}
                  </button>
                  {isDetailExpanded && (
                    <pre className="mt-1 max-h-56 overflow-y-auto rounded bg-black/40 p-2 text-[10px] text-left text-textMuted whitespace-pre-wrap">
                      {displayEntry.detail}
                    </pre>
                  )}
                </div>
              )}
              {showApprovalInEntry && (
                <div className="mt-2 flex justify-end border-t border-white/5 pt-2">
                  <Link
                    href="/approvals"
                    className="inline-flex items-center gap-1.5 rounded border border-accent/50 bg-accent/10 px-2 py-1.5 font-mono text-[10px] font-medium text-accent hover:bg-accent/20"
                  >
                    <StreamPlanningIcon className="h-3.5 w-3.5" />
                    Review approvals
                  </Link>
                </div>
              )}
              {displayEntry.meta?.documentId && (
                <div className="mt-2 flex justify-end border-t border-white/5 pt-2">
                  <Link
                    href={`/planning-documents/${displayEntry.meta.documentId}`}
                    className="inline-flex items-center gap-1.5 rounded border border-agentCyan/50 bg-agentCyan/10 px-2 py-1.5 font-mono text-[10px] font-medium text-agentCyan hover:bg-agentCyan/20"
                  >
                    <StreamPlanningIcon className="h-3.5 w-3.5" />
                    View document
                  </Link>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
