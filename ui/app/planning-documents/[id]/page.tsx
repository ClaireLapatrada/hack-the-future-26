"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { LayoutShell } from "../../../components/LayoutShell";

type PlanningDocument = {
  id: string;
  slug: string;
  title: string;
  createdAt: string;
  situationSummary: string;
  recommendedScenario: string;
  scenarioComparison: Array<{
    scenario_id?: string;
    scenario_name?: string;
    expected_cost_increase_usd?: number;
    expected_service_level?: string;
    average_score?: number;
    description?: string;
  }>;
  costImpactSummary: string;
  serviceLevelImpact: string;
  documentType: string;
  affectedItemId?: string;
  riskAppetite?: string;
};

function DocIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor" aria-hidden>
      <path
        fillRule="evenodd"
        d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function ArrowLeftIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor" aria-hidden>
      <path
        fillRule="evenodd"
        d="M17 10a.75.75 0 01-.75.75H5.612l4.158 3.96a.75.75 0 11-1.04 1.08l-5.5-5.25a.75.75 0 010-1.08l5.5-5.25a.75.75 0 111.04 1.08L5.612 9.25H16.25A.75.75 0 0117 10z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function formatDate(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export default function PlanningDocumentDetailPage() {
  const params = useParams();
  const id = typeof params.id === "string" ? params.id : "";
  const [doc, setDoc] = useState<PlanningDocument | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    fetch(`/api/planning-documents/${id}`)
      .then((res) => {
        if (!res.ok) throw new Error("Document not found");
        return res.json();
      })
      .then((data: PlanningDocument) => setDoc(data))
      .catch((e) => setLoadError(e instanceof Error ? e.message : "Failed to load"));
  }, [id]);

  if (loadError || (!doc && id)) {
    return (
      <LayoutShell title="Planning Document" subtitle="">
        <div className="glass-card p-6 text-center">
          <p className="text-danger">{loadError ?? "Document not found."}</p>
          <Link
            href="/planning-documents"
            className="mt-4 inline-flex items-center gap-2 text-agentCyan hover:underline"
          >
            <ArrowLeftIcon className="h-4 w-4" />
            Back to Planning documents
          </Link>
        </div>
      </LayoutShell>
    );
  }

  if (!doc) {
    return (
      <LayoutShell title="Planning Document" subtitle="">
        <div className="glass-card p-6 text-center text-textMuted">Loading…</div>
      </LayoutShell>
    );
  }

  return (
    <LayoutShell
      title={doc.title}
      subtitle={`${formatDate(doc.createdAt)} · ${doc.id}`}
    >
      <div className="flex h-full min-h-0 flex-col gap-6 overflow-y-auto">
        <Link
          href="/planning-documents"
          className="inline-flex w-fit items-center gap-2 text-[11px] font-medium text-textMuted hover:text-agentCyan"
        >
          <ArrowLeftIcon className="h-3.5 w-3.5" />
          Back to Planning documents
        </Link>

        <div className="glass-card p-4">
          <h3 className="mb-2 font-mono text-xs font-semibold uppercase tracking-wide text-textMuted">
            Situation
          </h3>
          <p className="text-sm text-textPrimary whitespace-pre-wrap">
            {doc.situationSummary}
          </p>
        </div>

        <div className="glass-card border-agentCyan/30 p-4">
          <h3 className="mb-2 font-mono text-xs font-semibold uppercase tracking-wide text-agentCyan">
            Recommended scenario
          </h3>
          <p className="text-sm font-medium text-textPrimary">
            {doc.recommendedScenario}
          </p>
          {doc.costImpactSummary && (
            <p className="mt-2 text-[11px] text-textMuted">
              {doc.costImpactSummary}
            </p>
          )}
          {doc.serviceLevelImpact && (
            <p className="mt-1 text-[11px] text-textMuted">
              Service level: {doc.serviceLevelImpact}
            </p>
          )}
        </div>

        {doc.scenarioComparison && doc.scenarioComparison.length > 0 && (
          <div className="glass-card p-4">
            <h3 className="mb-3 font-mono text-xs font-semibold uppercase tracking-wide text-textMuted">
              Scenario comparison
            </h3>
            <ul className="space-y-2">
              {doc.scenarioComparison.map((s, i) => (
                <li
                  key={i}
                  className="flex flex-wrap items-baseline justify-between gap-2 rounded border border-white/5 bg-surfaceMuted/50 px-3 py-2 text-[11px]"
                >
                  <span className="font-medium text-textPrimary">
                    {s.scenario_name ?? s.scenario_id ?? `Scenario ${i + 1}`}
                  </span>
                  <span className="font-mono text-textMuted">
                    {s.expected_cost_increase_usd != null &&
                      `$${s.expected_cost_increase_usd.toLocaleString()}`}
                    {s.expected_service_level && ` · ${s.expected_service_level}`}
                    {s.average_score != null && ` · score ${s.average_score}`}
                  </span>
                  {s.description && (
                    <span className="w-full text-textMuted mt-1 block">
                      {s.description}
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}

        {(doc.affectedItemId || doc.riskAppetite) && (
          <div className="glass-card p-4">
            <h3 className="mb-2 font-mono text-xs font-semibold uppercase tracking-wide text-textMuted">
              Context
            </h3>
            <p className="text-[11px] text-textMuted">
              {doc.affectedItemId && <>Affected item: {doc.affectedItemId}</>}
              {doc.affectedItemId && doc.riskAppetite && " · "}
              {doc.riskAppetite && <>Risk appetite: {doc.riskAppetite}</>}
            </p>
          </div>
        )}
      </div>
    </LayoutShell>
  );
}
