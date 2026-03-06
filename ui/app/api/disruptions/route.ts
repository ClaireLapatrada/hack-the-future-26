import { NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

export type DisruptionListItem = {
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

export async function GET() {
  try {
    const res = await fetch(`${BACKEND_URL}/api/disruptions`, { cache: "no-store" });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (e) {
    console.error("Failed to load disruption history:", e);
    return NextResponse.json(
      { error: "Failed to load disruption history" },
      { status: 500 }
    );
  }
}
