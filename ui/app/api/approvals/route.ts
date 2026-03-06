import { NextResponse } from "next/server";
import path from "path";
import fs from "fs";

const DATA_ROOT = process.cwd();

/** Resolve data directory: use ui/data when running from project root, else data under cwd */
function getDataPath(filename: string): string {
  const underCwd = path.join(DATA_ROOT, filename);
  const underUi = path.join(DATA_ROOT, "ui", filename);
  if (fs.existsSync(underCwd)) return underCwd;
  if (fs.existsSync(underUi)) return underUi;
  // New file: write to ui/data when cwd is project root so we match where Python writes
  const inUi = path.basename(DATA_ROOT) === "ui";
  return inUi ? underCwd : underUi;
}

const PENDING_APPROVALS_FILE = "data/pending_approvals.json";
const RESOLUTIONS_FILE = "data/approval_resolutions.json";
const MOCK_HISTORY_FILE = "data/mock_disruption_history.json";

function readJson<T>(filename: string): T {
  const filePath = getDataPath(filename);
  const raw = fs.readFileSync(filePath, "utf-8");
  return JSON.parse(raw) as T;
}

function writeJson(filename: string, data: unknown): void {
  const filePath = getDataPath(filename);
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, JSON.stringify(data, null, 2), "utf-8");
}

function dataFileExists(filename: string): boolean {
  return fs.existsSync(getDataPath(filename));
}

type DisruptionEvent = {
  event_id: string;
  date: string;
  type: string;
  region: string;
  severity: string;
  description: string;
  mitigation_taken?: {
    action: string;
    cost_usd?: number | null;
    outcome: string;
  };
  impact?: { revenue_at_risk_usd?: number | null };
  lessons_learned?: string;
  logged_at?: string;
};

type PendingApprovalEntry = {
  id: string;
  severity: string;
  title: string;
  situation: string;
  recommendation: string;
  confidence: string;
  auditLog: Array<{ time: string; text: string }>;
  status?: string;
  createdAt?: string;
};

export type ApprovalItem = {
  id: string;
  severity: "CRITICAL" | "HIGH" | "MEDIUM";
  title: string;
  age: string;
  situation: string;
  recommendation: string;
  confidence: string;
  auditLog: Array<{ time: string; text: string }>;
};

function formatAge(dateStr: string): string {
  const dt = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - dt.getTime();
  const diffM = Math.floor(diffMs / 60000);
  const diffH = Math.floor(diffM / 60);
  if (diffM < 60) return `${diffM} min ago`;
  if (diffH < 24) return `${diffH}h ago`;
  return `${Math.floor(diffH / 24)}d ago`;
}

function normalizeSeverity(s: string): "CRITICAL" | "HIGH" | "MEDIUM" {
  const u = (s || "").toUpperCase();
  if (u === "CRITICAL") return "CRITICAL";
  if (u === "HIGH") return "HIGH";
  return "MEDIUM";
}

export async function GET() {
  try {
    const approvals: ApprovalItem[] = [];

    // 1. Agent-generated pending approvals (from planning/action tools)
    if (dataFileExists(PENDING_APPROVALS_FILE)) {
      try {
        const raw = readJson<PendingApprovalEntry[]>(PENDING_APPROVALS_FILE);
        const list = Array.isArray(raw) ? raw : [];
        for (const e of list) {
          if (e.status !== "pending" && e.status !== undefined) continue;
          approvals.push({
            id: e.id,
            severity: normalizeSeverity(e.severity),
            title: e.title,
            age: formatAge(e.createdAt ?? ""),
            situation: e.situation,
            recommendation: e.recommendation,
            confidence: e.confidence ?? "90%",
            auditLog: e.auditLog ?? [],
          });
        }
      } catch {
        // ignore
      }
    }

    // 2. Mock disruption history — Pending outcome, not yet resolved
    let resolutions: Record<string, string> = {};
    if (dataFileExists(RESOLUTIONS_FILE)) {
      try {
        resolutions = readJson<Record<string, string>>(RESOLUTIONS_FILE);
      } catch {
        // ignore
      }
    }

    if (dataFileExists(MOCK_HISTORY_FILE)) {
      try {
        const disruptions = readJson<DisruptionEvent[]>(MOCK_HISTORY_FILE);
        const pending = disruptions.filter(
          (d) =>
            d.mitigation_taken?.outcome === "Pending" &&
            !resolutions[d.event_id]
        );
        for (const d of pending) {
          const action = d.mitigation_taken?.action ?? "Pending";
          const rev = d.impact?.revenue_at_risk_usd;
          const impactStr =
            rev != null && true
              ? `Revenue at risk: $${(rev / 1_000_000).toFixed(2)}M. `
              : "";
          approvals.push({
            id: d.event_id,
            severity: normalizeSeverity(d.severity),
            title: `${d.type} — ${d.region}`,
            age: formatAge(d.logged_at ?? d.date),
            situation: `${impactStr}${d.description}`,
            recommendation: `APPROVE — ${action}`,
            confidence: "90%",
            auditLog: [
              { time: "—", text: d.description },
              { time: "—", text: action },
            ],
          });
        }
      } catch {
        // ignore
      }
    }

    // Deduplicate approval items by id
    const seen = new Set<string>();
    const unique = approvals.filter((a) => {
      if (seen.has(a.id)) return false;
      seen.add(a.id);
      return true;
    });
    approvals.length = 0;
    approvals.push(...unique);

    // Newest first (by id: APPR- and EVT- sort by date)
    approvals.sort((a, b) => {
      const aIsAppr = a.id.startsWith("APPR-");
      const bIsAppr = b.id.startsWith("APPR-");
      if (aIsAppr && bIsAppr) return b.id.localeCompare(a.id);
      if (aIsAppr) return -1;
      if (bIsAppr) return 1;
      return b.id.localeCompare(a.id);
    });

    return NextResponse.json(approvals);
  } catch (e) {
    console.error("Failed to load approvals:", e);
    return NextResponse.json(
      { error: "Failed to load approvals" },
      { status: 500 }
    );
  }
}

/** PATCH /api/approvals — body: { id: string, action: "approve" | "reject" } */
export async function PATCH(request: Request) {
  try {
    const body = await request.json();
    const id = typeof body?.id === "string" ? body.id.trim() : "";
    const action =
      body?.action === "approve" || body?.action === "reject" ? body.action : null;
    if (!id || !action) {
      return NextResponse.json(
        { error: "Missing or invalid id or action (use approve/reject)" },
        { status: 400 }
      );
    }

    if (id.startsWith("APPR-") || id.startsWith("RST-")) {
      if (!dataFileExists(PENDING_APPROVALS_FILE)) {
        return NextResponse.json({ error: "Approval not found" }, { status: 404 });
      }
      const list = readJson<PendingApprovalEntry[]>(PENDING_APPROVALS_FILE);
      const idx = list.findIndex(
        (e) => e.id === id && (e.status === "pending" || e.status === undefined)
      );
      // Fall back to first match if no pending entry found (for safety)
      const resolveIdx = idx !== -1 ? idx : list.findIndex((e) => e.id === id);

      if (resolveIdx === -1) {
        return NextResponse.json({ error: "Approval not found" }, { status: 404 });
      }
      list[resolveIdx].status = action === "approve" ? "approved" : "rejected";
      writeJson(PENDING_APPROVALS_FILE, list);
      return NextResponse.json({ ok: true, id, status: list[resolveIdx].status });
    }

    // Mock event_id (EVT-*): store resolution so GET excludes it from pending
    if (id.startsWith("EVT-")) {
      let resolutions: Record<string, string> = {};
      if (dataFileExists(RESOLUTIONS_FILE)) {
        resolutions = readJson<Record<string, string>>(RESOLUTIONS_FILE);
      }
      resolutions[id] = action === "approve" ? "approved" : "rejected";
      writeJson(RESOLUTIONS_FILE, resolutions);
      return NextResponse.json({ ok: true, id, status: resolutions[id] });
    }

    return NextResponse.json({ error: "Unknown approval id format" }, { status: 400 });
  } catch (e) {
    console.error("Failed to update approval:", e);
    return NextResponse.json(
      { error: "Failed to update approval" },
      { status: 500 }
    );
  }
}
