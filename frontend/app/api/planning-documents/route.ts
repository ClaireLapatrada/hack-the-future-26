import { NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

// These types are exported — PlanningDocumentSummary is imported by the planning-documents page.
export type PlanningDocumentSummary = {
  id: string;
  slug: string;
  title: string;
  createdAt: string;
  recommendedScenario: string;
  costImpactSummary: string;
  serviceLevelImpact: string;
  documentType: string;
  affectedItemId?: string;
  riskAppetite?: string;
};

export type PlanningDocument = PlanningDocumentSummary & {
  situationSummary: string;
  scenarioComparison: Array<{
    scenario_id?: string;
    scenario_name?: string;
    expected_cost_increase_usd?: number;
    expected_service_level?: string;
    average_score?: number;
    description?: string;
  }>;
};

/** GET /api/planning-documents — list all planning documents (newest first) */
export async function GET() {
  try {
    const res = await fetch(`${BACKEND_URL}/api/planning-documents`, {
      cache: "no-store",
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (e) {
    console.error("Failed to load planning documents:", e);
    return NextResponse.json(
      { error: "Failed to load planning documents" },
      { status: 500 }
    );
  }
}
