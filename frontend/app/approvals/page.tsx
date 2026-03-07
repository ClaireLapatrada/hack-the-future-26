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

type Supplier = {
  id: string;
  name: string;
  category: string;
  country: string;
};

type DraftEmailResult = {
  status: string;
  draft_email?: {
    to: string;
    subject: string;
    body: string;
    priority: string;
    draft_timestamp: string;
  };
  next_step?: string;
  reference_id?: string;
  message?: string;
};

// ── Icons ─────────────────────────────────────────────────────────────────────

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

function MailIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor" aria-hidden>
      <path d="M2.003 5.884L10 9.882l7.997-3.998A2 2 0 0016 4H4a2 2 0 00-1.997 1.884z" />
      <path d="M18 8.118l-8 4-8-4V14a2 2 0 002 2h12a2 2 0 002-2V8.118z" />
    </svg>
  );
}

function CopyIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor" aria-hidden>
      <path d="M8 3a1 1 0 011-1h2a1 1 0 110 2H9a1 1 0 01-1-1z" />
      <path d="M6 3a2 2 0 00-2 2v11a2 2 0 002 2h8a2 2 0 002-2V5a2 2 0 00-2-2 3 3 0 01-3 3H9a3 3 0 01-3-3z" />
    </svg>
  );
}

// ── Email Draft Modal ─────────────────────────────────────────────────────────

function EmailDraftModal({
  approval,
  suppliers,
  onClose,
}: {
  approval: ApprovalItem;
  suppliers: Supplier[];
  onClose: () => void;
}) {
  const [supplierId, setSupplierId] = useState(suppliers[0]?.id ?? "");
  const [supplierContact, setSupplierContact] = useState("");
  const [ask, setAsk] = useState(approval.recommendation);
  const [draft, setDraft] = useState<DraftEmailResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [sendStatus, setSendStatus] = useState<"idle" | "sending" | "sent" | "error">("idle");
  const [sendNote, setSendNote] = useState("");

  const selectedSupplier = suppliers.find((s) => s.id === supplierId);

  const handleDraft = async () => {
    setLoading(true);
    setError(null);
    setDraft(null);
    try {
      const res = await fetch("/api/email/draft", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          supplier_name: selectedSupplier?.name ?? supplierId,
          supplier_contact: supplierContact || `procurement@${supplierId.toLowerCase()}.com`,
          disruption_context: approval.situation,
          ask,
        }),
      });
      const data = (await res.json()) as DraftEmailResult;
      if (data.status !== "success") throw new Error(data.message ?? "Draft failed");
      setDraft(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to generate draft");
    } finally {
      setLoading(false);
    }
  };

  const handleSend = async () => {
    if (!draft?.draft_email) return;
    setSendStatus("sending");
    setSendNote("");
    try {
      const res = await fetch("/api/email/send", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          supplier_name: selectedSupplier?.name ?? supplierId,
          supplier_contact: supplierContact || draft.draft_email.to,
          disruption_context: approval.situation,
          ask,
        }),
      });
      const data = (await res.json()) as DraftEmailResult & { sent?: boolean; send_note?: string };
      setSendStatus(data.sent ? "sent" : "idle");
      setSendNote(data.send_note ?? "");
    } catch (e) {
      setSendStatus("error");
      setSendNote("Send failed");
    }
  };

  const handleCopy = () => {
    if (!draft?.draft_email) return;
    const text = `To: ${draft.draft_email.to}\n${draft.draft_email.subject}\n\n${draft.draft_email.body}`;
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="flex w-full max-w-2xl flex-col rounded-xl border border-white/10 bg-surface shadow-2xl" style={{ maxHeight: "90vh" }}>
        {/* Header */}
        <div className="flex shrink-0 items-center justify-between border-b border-white/5 px-5 py-4">
          <div className="flex items-center gap-2">
            <MailIcon className="h-5 w-5 text-accent" />
            <h2 className="font-mono text-sm font-semibold text-textPrimary">Draft Supplier Email</h2>
          </div>
          <button onClick={onClose} className="text-textMuted hover:text-textPrimary">
            <XIcon className="h-4 w-4" />
          </button>
        </div>

        {/* Body — scrollable */}
        <div className="min-h-0 flex-1 overflow-y-auto p-5">
          <div className="space-y-3 text-xs">
            {/* Context from approval */}
            <div className="rounded-lg border border-agentCyan/30 bg-agentCyan/5 px-3 py-2 text-[11px]">
              <span className="font-mono font-semibold text-agentCyan">Context: </span>
              <span className="text-textMuted">{approval.situation.slice(0, 180)}{approval.situation.length > 180 ? "…" : ""}</span>
            </div>

            {/* Supplier selector */}
            <div className="grid grid-cols-2 gap-3">
              <div className="flex flex-col gap-1">
                <label className="font-mono text-[10px] uppercase tracking-wider text-textMuted">Supplier</label>
                <select
                  className="glass-input"
                  value={supplierId}
                  onChange={(e) => setSupplierId(e.target.value)}
                >
                  {suppliers.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name} ({s.country})
                    </option>
                  ))}
                  <option value="custom">— Custom —</option>
                </select>
              </div>
              <div className="flex flex-col gap-1">
                <label className="font-mono text-[10px] uppercase tracking-wider text-textMuted">
                  Supplier Contact Email
                </label>
                <input
                  className="glass-input"
                  type="email"
                  placeholder="procurement@supplier.com"
                  value={supplierContact}
                  onChange={(e) => setSupplierContact(e.target.value)}
                />
              </div>
            </div>

            {/* Ask */}
            <div className="flex flex-col gap-1">
              <label className="font-mono text-[10px] uppercase tracking-wider text-textMuted">
                Request / Ask
              </label>
              <textarea
                className="glass-input min-h-[60px] resize-y"
                value={ask}
                onChange={(e) => setAsk(e.target.value)}
              />
            </div>

            <button
              onClick={handleDraft}
              disabled={loading}
              className="flex w-full items-center justify-center gap-2 rounded-lg border border-agentCyan/50 bg-agentCyan/10 py-2.5 font-mono text-xs text-agentCyan disabled:opacity-60"
            >
              <MailIcon className="h-3.5 w-3.5" />
              {loading ? "Generating…" : "Generate Draft"}
            </button>

            {error && <p className="text-[11px] text-danger">{error}</p>}

            {draft?.draft_email && (
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-[10px] uppercase tracking-wide text-textMuted">
                    Draft Preview
                  </span>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[10px] text-textMuted">{draft.reference_id}</span>
                    <button
                      onClick={handleCopy}
                      className="flex items-center gap-1 rounded border border-white/10 bg-surfaceMuted px-2 py-1 font-mono text-[10px] text-textMuted hover:text-textPrimary"
                    >
                      <CopyIcon className="h-3 w-3" />
                      {copied ? "Copied!" : "Copy"}
                    </button>
                  </div>
                </div>
                <div className="rounded-lg border border-white/5 bg-surfaceMuted px-3 py-3">
                  <div className="mb-2 border-b border-white/5 pb-2 text-[10px] text-textMuted">
                    <span className="font-mono">To:</span> {draft.draft_email.to}
                    <br />
                    <span className="font-mono">Subject:</span> {draft.draft_email.subject}
                    <br />
                    <span className="font-mono">Priority:</span> {draft.draft_email.priority}
                  </div>
                  <pre className="whitespace-pre-wrap font-mono text-[10px] leading-relaxed text-textPrimary">
                    {draft.draft_email.body}
                  </pre>
                </div>
                <p className="text-[10px] text-textMuted">{draft.next_step}</p>
              </div>
            )}

            {sendNote && (
              <p className={`font-mono text-[11px] ${sendStatus === "sent" ? "text-success" : sendStatus === "error" ? "text-danger" : "text-textMuted"}`}>
                {sendNote}
              </p>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex shrink-0 items-center justify-between border-t border-white/5 px-5 py-3">
          <button onClick={onClose} className="rounded-lg border border-white/10 bg-surfaceMuted px-4 py-2 font-mono text-xs text-textMuted hover:text-textPrimary">
            Close
          </button>
          {draft?.draft_email && (
            <button
              onClick={handleSend}
              disabled={sendStatus === "sending" || sendStatus === "sent"}
              className="flex items-center gap-2 rounded-lg bg-accent px-4 py-2 font-mono text-xs font-semibold text-black hover:bg-accentSoft disabled:opacity-60"
            >
              <MailIcon className="h-3.5 w-3.5" />
              {sendStatus === "sending" ? "Sending…" : sendStatus === "sent" ? "Sent!" : "Send Email"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function ApprovalsPage() {
  const [approvals, setApprovals] = useState<ApprovalItem[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [emailModalOpen, setEmailModalOpen] = useState(false);

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
    const interval = setInterval(fetchApprovals, 30_000);
    const onVisible = () => { if (document.visibilityState === "visible") fetchApprovals(); };
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      clearInterval(interval);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, []);

  // Load suppliers for email modal
  useEffect(() => {
    fetch("/api/profile")
      .then((r) => r.ok ? r.json() : Promise.reject(""))
      .then((d: { suppliers?: Supplier[] }) => setSuppliers(d.suppliers ?? []))
      .catch(() => {});
  }, []);

  const selected = selectedId ? approvals.find((a) => a.id === selectedId) ?? approvals[0] : approvals[0];

  return (
    <LayoutShell
      title="Approval Inbox"
      subtitle="Human-in-the-loop review — agent mitigation actions require your sign-off."
    >
      <div className="flex h-full min-h-0 gap-4">
        {/* Left: Pending list */}
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

        {/* Right: Detail panel */}
        <section className="flex min-h-0 flex-1 flex-col overflow-hidden">
          <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto pb-2">
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
                    <p className="text-agentCyan">{selected.recommendation}</p>
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
                    <button
                      onClick={() => setEmailModalOpen(true)}
                      className="flex items-center justify-center gap-2 rounded-lg border border-accent/50 bg-accent/10 px-4 py-2.5 font-mono text-xs text-accent hover:bg-accent/20"
                    >
                      <MailIcon className="h-4 w-4" />
                      Draft Email
                    </button>
                  </div>
                </div>

                <div className="glass-card flex flex-col p-4">
                  <h3 className="mb-3 text-xs font-semibold text-textMuted">Audit Log</h3>
                  <ul className="space-y-3">
                    {selected.auditLog.map((entry, i) => (
                      <li key={i} className="flex gap-2 text-[11px]">
                        <ClipboardIcon className="mt-0.5 h-4 w-4 shrink-0 text-textMuted" />
                        <div>
                          <span className="font-mono text-textMuted">ADK Agent · {entry.time}</span>
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

      {emailModalOpen && selected && (
        <EmailDraftModal
          approval={selected}
          suppliers={suppliers}
          onClose={() => setEmailModalOpen(false)}
        />
      )}
    </LayoutShell>
  );
}
