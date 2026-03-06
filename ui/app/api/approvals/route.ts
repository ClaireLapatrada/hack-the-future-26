import { NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

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

export async function GET() {
  try {
    const res = await fetch(`${BACKEND_URL}/api/approvals`, { cache: "no-store" });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (e) {
    console.error("Failed to load approvals:", e);
    return NextResponse.json({ error: "Failed to load approvals" }, { status: 500 });
  }
}

/** PATCH /api/approvals — body: { id: string, action: "approve" | "reject" } */
export async function PATCH(request: Request) {
  try {
    const body = await request.json();
    const id = typeof body?.id === "string" ? body.id.trim() : "";
    if (!id) {
      return NextResponse.json(
        { error: "Missing or invalid id" },
        { status: 400 }
      );
    }
    const res = await fetch(
      `${BACKEND_URL}/api/approvals/${encodeURIComponent(id)}`,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }
    );
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (e) {
    console.error("Failed to update approval:", e);
    return NextResponse.json({ error: "Failed to update approval" }, { status: 500 });
  }
}
