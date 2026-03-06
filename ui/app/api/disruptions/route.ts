import { NextResponse } from "next/server";
import path from "path";
import fs from "fs";
import { fetchNewsDisruptions } from "../../../lib/news-disruptions";

const DATA_ROOT = process.cwd();

type ActiveDisruptionConfig = {
  active: boolean;
  supplier_health_degraded?: boolean;
  shipping_lanes?: Record<
    string,
    { status: string; severity?: string; avg_delay_days?: number; reroute_via?: string; [key: string]: unknown }
  >;
};

function formatTime(isoOrDateStr: string): string {
  if (!isoOrDateStr) return "—";
  const d = new Date(isoOrDateStr);
  if (Number.isNaN(d.getTime())) return isoOrDateStr;
  return d.toISOString().replace("T", " ").slice(0, 19);
}

function readJson<T>(filename: string): T {
  const filePath = path.join(DATA_ROOT, filename);
  const raw = fs.readFileSync(filePath, "utf-8");
  return JSON.parse(raw) as T;
}

/** Read full active_disruption from repo root (../config) if present, else ui/config. */
function readFullActiveDisruptionConfig(): ActiveDisruptionConfig {
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
  return { active: false };
}

/** Legacy: read only active flag. */
function readActiveDisruptionConfig(): { active: boolean } {
  return readFullActiveDisruptionConfig();
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
  /** Optional: explicit timeline entries from real data. When present, used as-is. */
  timeline?: Array<{ time: string; text: string; muted?: boolean }>;
};

export type DisruptionListItem = {
  id: string;
  impact: string;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  title: string;
  tags: string[];
  description: string;
  timeline: Array<{ time: string; text: string; muted?: boolean }>;
  /** Optional: source domain or URL for real-world articles */
  source?: string;
  url?: string;
};

function toSeverity(s: string): "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" {
  const u = s?.toUpperCase() ?? "";
  if (u === "CRITICAL") return "CRITICAL";
  if (u === "HIGH") return "HIGH";
  if (u === "MEDIUM") return "MEDIUM";
  return "LOW";
}

function formatImpact(d: DisruptionEvent): string {
  const rev = d.impact?.revenue_at_risk_usd;
  if (rev != null && typeof rev === "number") {
    if (rev >= 1_000_000) return `$${(rev / 1_000_000).toFixed(1)}M`;
    if (rev >= 1_000) return `$${(rev / 1_000).toFixed(0)}K`;
    return `$${rev}`;
  }
  return "—";
}

function buildTimeline(d: DisruptionEvent): Array<{ time: string; text: string; muted?: boolean }> {
  if (d.timeline && Array.isArray(d.timeline) && d.timeline.length > 0) {
    return d.timeline.map((e) => ({
      time: e.time?.includes(":") ? e.time : formatTime(e.time),
      text: e.text ?? "",
      muted: e.muted,
    }));
  }
  const entries: Array<{ time: string; text: string; muted?: boolean }> = [];
  const hasLoggedAt = d.logged_at && !Number.isNaN(new Date(d.logged_at).getTime());
  const t0 = hasLoggedAt ? d.logged_at! : d.date;
  entries.push({ time: formatTime(t0), text: d.description });
  if (d.mitigation_taken?.action) {
    entries.push({
      time: formatTime(t0),
      text: `Mitigation: ${d.mitigation_taken.action}`,
      muted: true,
    });
  }
  if (d.lessons_learned) {
    entries.push({ time: formatTime(t0), text: d.lessons_learned, muted: true });
  }
  return entries.length > 0 ? entries : [{ time: "—", text: "No timeline data." }];
}

export async function GET() {
  try {
    const realItems = await fetchNewsDisruptions();
    if (realItems.length > 0) {
      return NextResponse.json(realItems);
    }
    const activeDisruption = readFullActiveDisruptionConfig();
    if (!activeDisruption.active) {
      return NextResponse.json([]);
    }
    const lanes = activeDisruption.shipping_lanes ?? {};
    const disruptedLanes = Object.entries(lanes).filter(
      ([, data]) => data && data.status === "DISRUPTED"
    );
    if (disruptedLanes.length > 0) {
      const now = new Date().toISOString();
      const items: DisruptionListItem[] = disruptedLanes.map(([laneName, data]) => {
        const severity = (data.severity ?? "High").toUpperCase();
        const delayDays = data.avg_delay_days ?? 14;
        const id = "initiated-" + laneName.replace(/\s+/g, "-").toLowerCase().replace(/[^a-z0-9-]/g, "");
        const sev: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" =
          severity === "CRITICAL" ? "CRITICAL" : severity === "HIGH" ? "HIGH" : severity === "MEDIUM" ? "MEDIUM" : "LOW";
        return {
          id,
          impact: `${delayDays}d delay`,
          severity: sev,
          title: `${laneName} — disrupted (${delayDays} day delay)`,
          tags: ["Shipping", laneName, "Initiated"],
          description: `Lane ${laneName} is reported disrupted with estimated ${delayDays}-day delay.${data.reroute_via ? ` Reroute via ${data.reroute_via}.` : ""} Initiated via scripts/initiate_event.py for demo.`,
          timeline: [
            { time: formatTime(now), text: `Disruption initiated: ${laneName} — ${delayDays} day(s) delay.` },
          ],
        };
      });
      return NextResponse.json(items);
    }
    const data = readJson<DisruptionEvent[]>("data/mock_disruption_history.json");
    const items: DisruptionListItem[] = data.map((d) => ({
      id: d.event_id,
      impact: formatImpact(d),
      severity: toSeverity(d.severity),
      title: d.description.slice(0, 70) + (d.description.length > 70 ? "…" : ""),
      tags: [d.type, d.region].filter(Boolean),
      description: d.description,
      timeline: buildTimeline(d),
    }));
    return NextResponse.json(items);
  } catch (e) {
    console.error("Failed to load disruption history:", e);
    return NextResponse.json(
      { error: "Failed to load disruption history" },
      { status: 500 }
    );
  }
}
