import { NextResponse } from "next/server";
import path from "path";
import fs from "fs";

const DATA_ROOT = process.cwd();
const RULES_PATH = path.join(DATA_ROOT, "config", "rules.json");

function readJson<T>(filename: string): T {
  const filePath = path.join(DATA_ROOT, filename);
  const raw = fs.readFileSync(filePath, "utf-8");
  return JSON.parse(raw) as T;
}

function writeRulesConfig(config: RulesConfig): void {
  fs.writeFileSync(RULES_PATH, JSON.stringify(config, null, 2), "utf-8");
}

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
    const data = readJson<RulesConfig>("config/rules.json");
    return NextResponse.json(data);
  } catch (e) {
    console.error("Failed to load rules config:", e);
    return NextResponse.json(
      { error: "Failed to load rules config" },
      { status: 500 }
    );
  }
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const nextValues = body.initialValues as Record<string, number | string | boolean> | undefined;
    if (!nextValues || typeof nextValues !== "object") {
      return NextResponse.json(
        { error: "Missing or invalid initialValues" },
        { status: 400 }
      );
    }

    const config = readJson<RulesConfig>("config/rules.json");
    config.initialValues = { ...config.initialValues, ...nextValues };
    writeRulesConfig(config);

    return NextResponse.json(config);
  } catch (e) {
    console.error("Failed to save rules config:", e);
    return NextResponse.json(
      { error: "Failed to save rules config" },
      { status: 500 }
    );
  }
}
