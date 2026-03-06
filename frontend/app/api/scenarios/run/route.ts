import { NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function POST(req: Request) {
  try {
    const body = await req.json().catch(() => ({}));
    const res = await fetch(`${BACKEND_URL}/api/scenarios/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (e) {
    console.error("Scenario run failed:", e);
    return NextResponse.json(
      { error: e instanceof Error ? e.message : "Failed to run scenario simulation" },
      { status: 500 }
    );
  }
}
