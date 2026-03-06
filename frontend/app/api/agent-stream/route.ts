import { NextResponse } from "next/server";

// Base URL of the FastAPI backend. Override with BACKEND_URL env var in .env.local.
const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

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

/** GET /api/agent-stream?context=dashboard|disruption&eventId=optional */
export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const params = new URLSearchParams();
    const context = searchParams.get("context");
    const eventId = searchParams.get("eventId");
    if (context) params.set("context", context);
    if (eventId) params.set("eventId", eventId);

    const qs = params.toString();
    const res = await fetch(`${BACKEND_URL}/api/agent-stream${qs ? `?${qs}` : ""}`, {
      cache: "no-store",
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (e) {
    console.error("Failed to load agent stream:", e);
    return NextResponse.json(
      { error: "Failed to load agent reasoning stream" },
      { status: 500 }
    );
  }
}
