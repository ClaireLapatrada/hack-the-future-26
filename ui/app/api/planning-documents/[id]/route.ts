import { NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

/** GET /api/planning-documents/[id] — get a single planning document by id */
export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const res = await fetch(
      `${BACKEND_URL}/api/planning-documents/${encodeURIComponent(id)}`,
      { cache: "no-store" }
    );
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (e) {
    console.error("Failed to load planning document:", e);
    return NextResponse.json(
      { error: "Failed to load planning document" },
      { status: 500 }
    );
  }
}
