import { NextResponse } from "next/server";
import path from "path";
import fs from "fs";

const DATA_ROOT = process.cwd();

function getDataPath(filename: string): string {
  const underCwd = path.join(DATA_ROOT, filename);
  const underUi = path.join(DATA_ROOT, "ui", filename);
  if (fs.existsSync(underCwd)) return underCwd;
  if (fs.existsSync(underUi)) return underUi;
  return path.basename(DATA_ROOT) === "ui" ? underCwd : underUi;
}

const PLANNING_DOCUMENTS_FILE = "data/planning_documents.json";

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

function readDocs(): PlanningDocument[] {
  const filePath = getDataPath(PLANNING_DOCUMENTS_FILE);
  if (!fs.existsSync(filePath)) return [];
  try {
    const raw = fs.readFileSync(filePath, "utf-8");
    const data = JSON.parse(raw);
    return Array.isArray(data) ? data : [];
  } catch {
    return [];
  }
}

/** GET /api/planning-documents — list all planning documents (newest first) */
export async function GET() {
  try {
    const docs = readDocs();
    const sorted = [...docs].sort(
      (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
    );
    return NextResponse.json(sorted);
  } catch (e) {
    console.error("Failed to load planning documents:", e);
    return NextResponse.json(
      { error: "Failed to load planning documents" },
      { status: 500 }
    );
  }
}
