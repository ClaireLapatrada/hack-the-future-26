import { NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function POST() {
  try {
    const res = await fetch(`${BACKEND_URL}/api/events/clear`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (e) {
    console.error("Failed to clear event:", e);
    return NextResponse.json({ error: "Failed to clear event" }, { status: 500 });
  }
}
