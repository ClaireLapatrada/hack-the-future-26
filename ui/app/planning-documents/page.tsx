"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { LayoutShell } from "../../components/LayoutShell";
import type { PlanningDocumentSummary } from "../api/planning-documents/route";

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

function ChevronRightIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor" aria-hidden>
      <path
        fillRule="evenodd"
        d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.06l-4.5 4.25a.75.75 0 01-1.06-.02z"
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

export default function PlanningDocumentsPage() {
  const [docs, setDocs] = useState<PlanningDocumentSummary[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/planning-documents")
      .then((res) => {
        if (!res.ok) throw new Error("Failed to load documents");
        return res.json();
      })
      .then((data: PlanningDocumentSummary[]) => setDocs(Array.isArray(data) ? data : []))
      .catch((e) => setLoadError(e instanceof Error ? e.message : "Failed to load"));
  }, []);

  return (
    <LayoutShell
      title="Past Crisis & Mitigation"
      subtitle="Internal planning documents from the Scenario Planning Agent. Use these as reference for service disruption mitigation."
    >
      <div className="flex h-full min-h-0 flex-col gap-6 overflow-y-auto">
        {/* Examples of mitigation plans */}
        <div className="glass-card border-agentCyan/20 p-4">
          <h2 className="mb-3 font-mono text-xs font-semibold uppercase tracking-wide text-agentCyan">
            Examples of mitigation plans for service disruptions
          </h2>
          <ul className="space-y-3 text-sm text-textPrimary">
            <li>
              <strong className="text-textPrimary">Supplier diversification</strong>
              <span className="text-textMuted"> — Average spend around 4% of procurement budget.</span>
            </li>
            <li>
              <strong className="text-textPrimary">Inventory buffering</strong>
              <span className="text-textMuted"> (safety stock) — Average spend around 10–20% of expected stock; cost 15–30% of total inventory.</span>
            </li>
          </ul>
          <p className="mt-3 text-[11px] text-textMuted">
            New documents are created automatically when the planning agent produces a recommendation (see agent stream on Dashboard or Disruptions for &quot;View document&quot;).
          </p>
        </div>

        {/* List of planning documents */}
        <div className="flex flex-1 flex-col min-h-0">
          <h2 className="mb-3 font-mono text-xs font-semibold uppercase tracking-wide text-textMuted">
            Planning documents ({docs.length})
          </h2>
          {loadError && (
            <p className="text-xs text-danger">{loadError}</p>
          )}
          {docs.length === 0 && !loadError && (
            <div className="glass-card p-6 text-center text-sm text-textMuted">
              <DocIcon className="mx-auto mb-2 h-10 w-10 text-textMuted/60" />
              <p>No planning documents yet.</p>
              <p className="mt-1 text-[11px]">
                Run a disruption cycle or scenario; when the agent creates a mitigation plan, it will appear here.
              </p>
            </div>
          )}
          <div className="min-h-0 flex-1 space-y-2 overflow-y-auto">
            {docs.map((doc) => (
              <Link
                key={doc.id}
                href={`/planning-documents/${doc.id}`}
                className="flex items-center gap-3 rounded-lg border border-white/5 bg-surface/80 px-4 py-3 transition hover:border-accent/30 hover:bg-surfaceMuted"
              >
                <DocIcon className="h-5 w-5 shrink-0 text-accent" />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-textPrimary">
                    {doc.title}
                  </p>
                  <p className="mt-0.5 text-[11px] text-textMuted">
                    {doc.recommendedScenario}
                    {doc.costImpactSummary && ` · ${doc.costImpactSummary}`}
                  </p>
                  <span className="mt-1 inline-block font-mono text-[10px] text-textMuted">
                    {formatDate(doc.createdAt)} · {doc.id}
                  </span>
                </div>
                <ChevronRightIcon className="h-4 w-4 shrink-0 text-textMuted" />
              </Link>
            ))}
          </div>
        </div>
      </div>
    </LayoutShell>
  );
}
