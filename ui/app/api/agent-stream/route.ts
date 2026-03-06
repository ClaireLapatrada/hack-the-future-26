import { NextResponse } from "next/server";
import path from "path";
import fs from "fs";

const DATA_ROOT = process.cwd();

export type StreamEntryType = "OBSERVE" | "ACTION" | "RESULT" | "REASON" | "REASONING" | "PLANNING" | "MEMORY" | "TOOL";

export type StreamEntry = {
  type: StreamEntryType;
  time: string;
  content: string;
  confidence?: string;
  category?: string;
  meta?: { documentId?: string };
  detail?: string;
};

function readJson<T>(filename: string): T {
  const filePath = path.join(DATA_ROOT, filename);
  const raw = fs.readFileSync(filePath, "utf-8");
  return JSON.parse(raw) as T;
}

/** GET /api/agent-stream?context=dashboard|disruption&eventId=optional
 * Returns agent reasoning stream entries. context and eventId allow future per-context or per-event streams.
 */
export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const context = searchParams.get("context") ?? "dashboard";
    const eventId = searchParams.get("eventId");

    // Default stream from data file; check for context-specific file first
    const defaultPath = "data/agent_reasoning_stream.json";
    const contextPath =
      context === "disruption" && eventId
        ? `data/agent_reasoning_stream_disruption_${eventId}.json`
        : context === "disruption"
          ? "data/agent_reasoning_stream_disruption.json"
          : defaultPath;

    let entries: StreamEntry[];
    const fullContextPath = path.join(DATA_ROOT, contextPath);
    if (fs.existsSync(fullContextPath)) {
      entries = readJson<StreamEntry[]>(contextPath);
    } else {
      entries = readJson<StreamEntry[]>(defaultPath);
    }

    if (!Array.isArray(entries)) {
      return NextResponse.json([]);
    }
    // Validate and normalize types; return newest first for display
    const valid: StreamEntry[] = entries
      .filter((e) => e && typeof e.content === "string")
      .map((e) => ({
        type: ["OBSERVE", "ACTION", "RESULT", "REASON", "REASONING", "PLANNING", "MEMORY", "TOOL"].includes(e.type) ? e.type : "OBSERVE",
        time: typeof e.time === "string" ? e.time : "—",
        content: e.content,
        ...(e.confidence != null && { confidence: String(e.confidence) }),
        ...(e.category != null && { category: String(e.category) }),
        ...(e.meta != null && typeof e.meta === "object" && { meta: e.meta }),
        ...(typeof (e as any).detail === "string" && { detail: (e as any).detail }),
      })) as StreamEntry[];

    return NextResponse.json(valid.reverse());
  } catch (e) {
    console.error("Failed to load agent stream:", e);
    return NextResponse.json(
      { error: "Failed to load agent reasoning stream" },
      { status: 500 }
    );
  }
}
