"use client";

import { useState, useEffect } from "react";
import { LayoutShell } from "../../components/LayoutShell";

type ApprovalItem = {
  id: string;
  severity: "CRITICAL" | "HIGH" | "MEDIUM";
  title: string;
  age: string;
  situation: string;
  recommendation: string;
  confidence: string;
  auditLog: Array<{ time: string; text: string }>;
};

function ClockIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden>
      <circle cx="10" cy="10" r="7" />
      <path d="M10 6v4l2.5 2.5" />
    </svg>
  );
}

function BellIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor" aria-hidden>
      <path
        fillRule="evenodd"
        d="M10 2a6 6 0 00-6 6c0 1.887.454 3.665 1.257 5.234C6.806 13.887 7 14.373 7 15a1 1 0 001 1h4a1 1 0 001-1c0-.627.194-1.113.743-2.766A7.998 7.998 0 0016 8a6 6 0 00-6-6zm0 16a2 2 0 01-2-2h4a2 2 0 01-2 2z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function CheckIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor" aria-hidden>
      <path
        fillRule="evenodd"
        d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function XIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor" aria-hidden>
      <path
        fillRule="evenodd"
        d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function ClipboardIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor" aria-hidden>
      <path
        fillRule="evenodd"
        d="M7 2a2 2 0 00-2 2v12a2 2 0 002 2h6a2 2 0 002-2V4a2 2 0 00-2-2h-1.5V3a1.5 1.5 0 01-1.5 1.5h-3A1.5 1.5 0 014 3v-.5A2 2 0 002 5v12a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2h-2V4a2 2 0 00-2-2H7zM5 3v-.5A.5.5 0 015.5 2h3a.5.5 0 01.5.5V3H5zm0 4h10v10H5V7z"
        clipRule="evenodd"
      />
    </svg>
  );
}

export default function ApprovalsPage() {
  const [approvals, setApprovals] = useState<ApprovalItem[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const fetchApprovals = () => {
    fetch("/api/approvals")
      .then((res) => {
        if (!res.ok) throw new Error("Failed to load approvals");
        return res.json();
      })
      .then((data: ApprovalItem[]) => {
        setApprovals(data);
        setSelectedId((prev) => {
          if (data.length === 0) return null;
          if (prev && data.some((a) => a.id === prev)) return prev;
          return data[0].id;
        });
      })
      .catch((e) => setLoadError(e instanceof Error ? e.message : "Failed to load"));
  };

  useEffect(() => {
    fetchApprovals();
  }, []);

  const selected = selectedId ? approvals.find((a) => a.id === selectedId) ?? approvals[0] : approvals[0];

  return (
    <LayoutShell
      title="Approval Inbox"
      subtitle="Human-in-the-loop review — agent mitigation actions require your sign-off."
    >
      <div className="flex h-full min-h-0 gap-4">
        {/* Left: Pending list in a card — scrollable */}
        <section className="flex w-[320px] shrink-0 flex-col">
          <div className="glass-card flex min-h-0 flex-1 flex-col p-3">
            <div className="mb-3 flex shrink-0 items-center gap-2">
              <h2 className="text-xs font-semibold text-textPrimary">
                Pending ({approvals.length})
              </h2>
              <ClockIcon className="h-4 w-4 text-textMuted" />
            </div>
            <div className="min-h-0 flex-1 space-y-2 overflow-y-auto">
            {loadError && <p className="text-xs text-danger">{loadError}</p>}
            {approvals.length === 0 && !loadError && <p className="text-xs text-textMuted">Loading…</p>}
            {approvals.map((a) => {
              const isSelected = selected && a.id === selected.id;
              return (
                <button
                  key={a.id}
                  onClick={() => setSelectedId(a.id)}
                  className={`flex w-full flex-col gap-1 rounded-lg border px-3 py-2.5 text-left transition ${
                    isSelected
                      ? "border-accent/50 bg-surfaceMuted"
                      : "border-white/5 bg-surface/80 hover:border-white/10"
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 text-[11px]">
                    <span
                      className={
                        a.severity === "CRITICAL"
                          ? "pill-critical"
                          : a.severity === "HIGH"
                            ? "pill-high"
                            : "pill-medium-severity"
                      }
                    >
                      {a.severity}
                    </span>
                    <span className="font-mono text-textMuted">{a.id}</span>
                  </div>
                  <p className="truncate text-xs font-medium text-textPrimary">
                    {a.title}
                  </p>
                  <span className="font-mono text-[11px] text-textMuted">
                    {a.age}
                  </span>
                </button>
              );
            })}
            </div>
          </div>
        </section>

        {/* Right: Detail panel — scrollable */}
          <section className="flex min-h-0 flex-1 flex-col overflow-hidden">
          <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto">
            {!selected ? (
              <div className="glass-card p-4 text-textMuted text-sm">Select an approval or wait for data.</div>
            ) : (
            <>
            <div className="glass-card p-4">
              <div className="mb-3 flex items-start gap-2">
                <BellIcon className="mt-0.5 h-5 w-5 shrink-0 text-accent" />
                <div>
                  <h3 className="font-mono text-base font-semibold tracking-tight text-textPrimary">
                    {selected.title}
                  </h3>
                  <p className="mt-2 text-[11px] text-textMuted">
                    {selected.situation}
                  </p>
                </div>
              </div>

              <div className="mb-4 rounded-lg border border-agentCyan/40 bg-agentCyan/10 p-3 text-[11px]">
                <div className="mb-1 flex items-center justify-between">
                  <span className="font-mono font-semibold uppercase tracking-wide text-agentCyan">
                    Agent Recommendation
                  </span>
                  <span className="font-mono text-agentCyan/80">
                    Confidence: {selected.confidence}
                  </span>
                </div>
                <p className="text-agentCyan">
                  {selected.recommendation}
                </p>
              </div>

              <div className="flex gap-3">
                <button
                  onClick={() => {
                    if (!selected) return;
                    fetch("/api/approvals", {
                      method: "PATCH",
                      headers: { "Content-Type": "application/json" },
                      body: JSON.stringify({ id: selected.id, action: "approve" }),
                    })
                      .then((r) => (r.ok ? fetchApprovals() : r.json().then((e) => Promise.reject(e))))
                      .catch((e) => setLoadError(e?.error ?? "Failed to approve"));
                  }}
                  className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-success px-4 py-2.5 font-mono text-xs font-semibold text-black"
                >
                  <CheckIcon className="h-4 w-4" />
                  Approve
                </button>
                <button
                  onClick={() => {
                    if (!selected) return;
                    fetch("/api/approvals", {
                      method: "PATCH",
                      headers: { "Content-Type": "application/json" },
                      body: JSON.stringify({ id: selected.id, action: "reject" }),
                    })
                      .then((r) => (r.ok ? fetchApprovals() : r.json().then((e) => Promise.reject(e))))
                      .catch((e) => setLoadError(e?.error ?? "Failed to reject"));
                  }}
                  className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-danger/90 px-4 py-2.5 font-mono text-xs font-semibold text-white"
                >
                  <XIcon className="h-4 w-4" />
                  Reject
                </button>
              </div>
            </div>

            <div className="glass-card flex flex-col p-4">
              <h3 className="mb-3 text-xs font-semibold text-textMuted">
                Audit Log
              </h3>
              <ul className="space-y-3">
                {selected.auditLog.map((entry, i) => (
                  <li key={i} className="flex gap-2 text-[11px]">
                    <ClipboardIcon className="mt-0.5 h-4 w-4 shrink-0 text-textMuted" />
                    <div>
                      <span className="font-mono text-textMuted">
                        ADK Agent · {entry.time}
                      </span>
                      <p className="mt-0.5 text-textPrimary">{entry.text}</p>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
            </>
            )}
          </div>
        </section>
      </div>
    </LayoutShell>
  );
}
