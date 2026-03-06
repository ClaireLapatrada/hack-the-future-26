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

function readDocs(): unknown[] {
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

/** GET /api/planning-documents/[id] — get a single planning document by id */
export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const docs = readDocs();
    const doc = (docs as Array<{ id?: string }>).find((d) => d.id === id);
    if (!doc) {
      return NextResponse.json(
        { error: "Planning document not found" },
        { status: 404 }
      );
    }
    return NextResponse.json(doc);
  } catch (e) {
    console.error("Failed to load planning document:", e);
    return NextResponse.json(
      { error: "Failed to load planning document" },
      { status: 500 }
    );
  }
}
