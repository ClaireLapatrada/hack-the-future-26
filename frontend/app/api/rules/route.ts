import { NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

type RulesConfig = {
  sections: Array<{
    group: string;
    icon: "box" | "user";
    rules: Array<
      | { type: "slider"; key: string; name: string; description: string; min: number; max: number; unit: string }
      | { type: "input"; key: string; name: string; description: string }
      | { type: "toggle"; key: string; name: string; description: string }
    >;
  }>;
  initialValues: Record<string, number | string | boolean>;
};

export async function GET() {
  try {
    const res = await fetch(`${BACKEND_URL}/api/rules`, { cache: "no-store" });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (e) {
    console.error("Failed to load rules config:", e);
    return NextResponse.json({ error: "Failed to load rules config" }, { status: 500 });
  }
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const res = await fetch(`${BACKEND_URL}/api/rules`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (e) {
    console.error("Failed to save rules config:", e);
    return NextResponse.json({ error: "Failed to save rules config" }, { status: 500 });
  }
}
