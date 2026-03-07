"use client";

import { useState, useEffect } from "react";
import { LayoutShell } from "../../components/LayoutShell";

// ── Icons ────────────────────────────────────────────────────────────────────

function SaveIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor" aria-hidden>
      <path d="M7.707 10.293a1 1 0 10-1.414 1.414l3 3a1 1 0 001.414 0l3-3a1 1 0 00-1.414-1.414L11 11.586V6h5a2 2 0 012 2v7a2 2 0 01-2 2H4a2 2 0 01-2-2V8a2 2 0 012-2h5v5.586l-1.293-1.293zM9 4a1 1 0 012 0v2H9V4z" />
    </svg>
  );
}

function PlusIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor" aria-hidden>
      <path fillRule="evenodd" d="M10 5a1 1 0 011 1v3h3a1 1 0 110 2h-3v3a1 1 0 11-2 0v-3H6a1 1 0 110-2h3V6a1 1 0 011-1z" clipRule="evenodd" />
    </svg>
  );
}

function TrashIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor" aria-hidden>
      <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
    </svg>
  );
}

function EditIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor" aria-hidden>
      <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
    </svg>
  );
}

function BoltIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor" aria-hidden>
      <path fillRule="evenodd" d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z" clipRule="evenodd" />
    </svg>
  );
}

function XIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor" aria-hidden>
      <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
    </svg>
  );
}

function CheckIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor" aria-hidden>
      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
    </svg>
  );
}

// ── Types ────────────────────────────────────────────────────────────────────

type CompanyInfo = {
  company_name: string;
  contact_email: string;
  sender_name: string;
};

type Supplier = {
  id: string;
  name: string;
  category: string;
  country: string;
  spend_pct: number;
  lead_time_days: number;
  single_source: boolean;
  contract_end: string;
  health_score: number;
};

type CustomerSLA = {
  customer: string;
  on_time_delivery_pct: number;
  penalty_per_day_usd: number;
};

type ProductionLine = {
  line_id: string;
  product: string;
  daily_output_units: number;
  semiconductor_dependent: boolean;
  daily_revenue_usd: number;
};

type InventoryPolicy = {
  target_buffer_days: number;
  reorder_threshold_days: number;
  max_buffer_days: number;
};

type Profile = {
  company_info: CompanyInfo;
  suppliers: Supplier[];
  customer_slas: CustomerSLA[];
  production_lines: ProductionLine[];
  inventory_policy: InventoryPolicy;
};

const LANE_OPTIONS = [
  "Asia-Europe (Suez)",
  "Trans-Pacific (LA)",
  "Europe-Americas (Atlantic)",
  "Asia-Pacific (ASEAN)",
];

const DEFAULT_SUPPLIER: Supplier = {
  id: "",
  name: "",
  category: "",
  country: "",
  spend_pct: 0,
  lead_time_days: 14,
  single_source: false,
  contract_end: "",
  health_score: 80,
};

const DEFAULT_SLA: CustomerSLA = {
  customer: "",
  on_time_delivery_pct: 98,
  penalty_per_day_usd: 10000,
};

const DEFAULT_LINE: ProductionLine = {
  line_id: "",
  product: "",
  daily_output_units: 1000,
  semiconductor_dependent: false,
  daily_revenue_usd: 50000,
};

// ── Inline field component ──────────────────────────────────────────────────

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      <label className="font-mono text-[10px] uppercase tracking-wider text-textMuted">{label}</label>
      {children}
    </div>
  );
}

// ── Supplier modal ───────────────────────────────────────────────────────────

function SupplierModal({
  supplier,
  onSave,
  onClose,
}: {
  supplier: Supplier;
  onSave: (s: Supplier) => void;
  onClose: () => void;
}) {
  const [form, setForm] = useState<Supplier>(supplier);
  const set = (k: keyof Supplier, v: Supplier[keyof Supplier]) =>
    setForm((p) => ({ ...p, [k]: v }));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="w-full max-w-lg rounded-xl border border-white/10 bg-surface p-6 shadow-2xl">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="font-mono text-sm font-semibold text-textPrimary">
            {supplier.id ? "Edit Supplier" : "Add Supplier"}
          </h2>
          <button onClick={onClose} className="text-textMuted hover:text-textPrimary">
            <XIcon className="h-4 w-4" />
          </button>
        </div>
        <div className="grid grid-cols-2 gap-3 text-xs">
          <Field label="Supplier ID">
            <input
              className="glass-input"
              value={form.id}
              onChange={(e) => set("id", e.target.value)}
              placeholder="SUP-005"
            />
          </Field>
          <Field label="Name">
            <input className="glass-input" value={form.name} onChange={(e) => set("name", e.target.value)} placeholder="Acme Semiconductors" />
          </Field>
          <Field label="Category">
            <input className="glass-input" value={form.category} onChange={(e) => set("category", e.target.value)} placeholder="Semiconductors" />
          </Field>
          <Field label="Country">
            <input className="glass-input" value={form.country} onChange={(e) => set("country", e.target.value)} placeholder="Taiwan" />
          </Field>
          <Field label="Spend %">
            <input
              className="glass-input"
              type="number"
              min={0}
              max={100}
              value={form.spend_pct}
              onChange={(e) => set("spend_pct", Number(e.target.value))}
            />
          </Field>
          <Field label="Lead Time (days)">
            <input
              className="glass-input"
              type="number"
              min={1}
              value={form.lead_time_days}
              onChange={(e) => set("lead_time_days", Number(e.target.value))}
            />
          </Field>
          <Field label="Contract End">
            <input
              className="glass-input"
              type="date"
              value={form.contract_end}
              onChange={(e) => set("contract_end", e.target.value)}
            />
          </Field>
          <Field label="Health Score (0–100)">
            <input
              className="glass-input"
              type="number"
              min={0}
              max={100}
              value={form.health_score}
              onChange={(e) => set("health_score", Number(e.target.value))}
            />
          </Field>
          <div className="col-span-2 flex items-center gap-2">
            <button
              type="button"
              role="switch"
              aria-checked={form.single_source}
              onClick={() => set("single_source", !form.single_source)}
              className={`relative inline-flex h-6 w-11 shrink-0 rounded-full transition-colors ${form.single_source ? "bg-accent" : "bg-surfaceMuted"}`}
            >
              <span className={`pointer-events-none inline-block h-5 w-5 translate-y-0.5 rounded-full bg-white shadow transition-transform ${form.single_source ? "translate-x-6" : "translate-x-0.5"}`} />
            </button>
            <span className="text-xs text-textPrimary">Single-source supplier</span>
          </div>
        </div>
        <div className="mt-5 flex justify-end gap-2">
          <button onClick={onClose} className="rounded-lg border border-white/10 bg-surfaceMuted px-4 py-2 font-mono text-xs text-textMuted hover:text-textPrimary">
            Cancel
          </button>
          <button
            onClick={() => onSave(form)}
            className="flex items-center gap-2 rounded-lg bg-accent px-4 py-2 font-mono text-xs font-semibold text-black hover:bg-accentSoft"
          >
            <CheckIcon className="h-3.5 w-3.5" />
            Save
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function SettingsPage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saveStatus, setSaveStatus] = useState<"idle" | "saving" | "saved" | "error">("idle");

  // Disruption simulation state
  const [simLane, setSimLane] = useState("Asia-Europe (Suez)");
  const [simDelay, setSimDelay] = useState(16);
  const [simStatus, setSimStatus] = useState<"idle" | "loading" | "ok" | "error">("idle");
  const [simMessage, setSimMessage] = useState("");

  // Supplier modal state
  const [supplierModal, setSupplierModal] = useState<{ supplier: Supplier; index: number | null } | null>(null);

  useEffect(() => {
    fetch("/api/profile")
      .then((r) => {
        if (!r.ok) throw new Error("Failed to load profile");
        return r.json();
      })
      .then((data: Profile) => setProfile(data))
      .catch((e) => setLoadError(e instanceof Error ? e.message : "Failed to load"));
  }, []);

  const save = async (updated: Profile) => {
    setSaveStatus("saving");
    try {
      const res = await fetch("/api/profile", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updated),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error((err as { detail?: string }).detail ?? "Failed to save");
      }
      const data = (await res.json()) as Profile;
      setProfile(data);
      setSaveStatus("saved");
      setTimeout(() => setSaveStatus("idle"), 2000);
    } catch (e) {
      setSaveStatus("error");
      setTimeout(() => setSaveStatus("idle"), 3000);
    }
  };

  const handleInitiate = async () => {
    setSimStatus("loading");
    setSimMessage("");
    try {
      const res = await fetch("/api/events/initiate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lane: simLane, delay_days: simDelay }),
      });
      const data = (await res.json()) as { ok?: boolean; message?: string; detail?: string };
      if (!res.ok) throw new Error(data.detail ?? "Failed");
      setSimStatus("ok");
      setSimMessage(data.message ?? "Disruption initiated.");
    } catch (e) {
      setSimStatus("error");
      setSimMessage(e instanceof Error ? e.message : "Failed to initiate");
    }
  };

  const handleClear = async () => {
    setSimStatus("loading");
    setSimMessage("");
    try {
      const res = await fetch("/api/events/clear", { method: "POST" });
      const data = (await res.json()) as { ok?: boolean; message?: string; detail?: string };
      if (!res.ok) throw new Error(data.detail ?? "Failed");
      setSimStatus("ok");
      setSimMessage(data.message ?? "Disruption cleared.");
    } catch (e) {
      setSimStatus("error");
      setSimMessage(e instanceof Error ? e.message : "Failed to clear");
    }
  };

  if (!profile && !loadError) {
    return (
      <LayoutShell title="Settings" subtitle="Configure your supply chain profile and simulation.">
        <p className="text-xs text-textMuted">Loading…</p>
      </LayoutShell>
    );
  }

  if (loadError || !profile) {
    return (
      <LayoutShell title="Settings" subtitle="Configure your supply chain profile and simulation.">
        <div className="glass-card p-4 text-xs">
          <p className="mb-3 text-danger">{loadError ?? "Unknown error"}</p>
          <p className="mb-3 text-textMuted">Make sure the backend is running: <code className="font-mono text-textPrimary">uvicorn backend.main:app --reload --port 8000</code></p>
          <button
            onClick={() => {
              setLoadError(null);
              fetch("/api/profile")
                .then((r) => { if (!r.ok) throw new Error("Failed to load profile"); return r.json(); })
                .then((data: Profile) => setProfile(data))
                .catch((e) => setLoadError(e instanceof Error ? e.message : "Failed to load"));
            }}
            className="rounded-lg border border-white/10 bg-surfaceMuted px-4 py-2 font-mono text-xs text-textMuted hover:text-textPrimary"
          >
            Retry
          </button>
        </div>
      </LayoutShell>
    );
  }

  const headerActions = (
    <div className="flex items-center gap-2">
      <button
        onClick={() => save(profile)}
        disabled={saveStatus === "saving"}
        className="flex items-center gap-2 rounded-lg bg-accent px-4 py-2 font-mono text-xs font-semibold text-black hover:bg-accentSoft disabled:opacity-60"
      >
        <SaveIcon className="h-3.5 w-3.5" />
        {saveStatus === "saving" ? "Saving…" : saveStatus === "saved" ? "Saved" : "Save All"}
      </button>
      {saveStatus === "error" && <span className="text-xs text-danger">Save failed</span>}
    </div>
  );

  return (
    <LayoutShell
      title="Settings & Onboarding"
      subtitle="Company profile, supplier data, and disruption simulation."
      headerRight={headerActions}
    >
      <div className="min-h-0 flex-1 space-y-4 overflow-y-auto text-xs pb-4">

        {/* ── Company Info ────────────────────────────────────────────── */}
        <section className="glass-card p-4">
          <div className="mb-3 font-mono text-[11px] font-semibold uppercase tracking-wide text-textMuted">
            Company Profile
          </div>
          <div className="grid grid-cols-3 gap-3">
            <Field label="Company Name">
              <input
                className="glass-input"
                value={profile.company_info.company_name}
                onChange={(e) =>
                  setProfile((p) => p && { ...p, company_info: { ...p.company_info, company_name: e.target.value } })
                }
              />
            </Field>
            <Field label="Contact Email">
              <input
                className="glass-input"
                type="email"
                value={profile.company_info.contact_email}
                onChange={(e) =>
                  setProfile((p) => p && { ...p, company_info: { ...p.company_info, contact_email: e.target.value } })
                }
              />
            </Field>
            <Field label="Sender Name (for emails)">
              <input
                className="glass-input"
                value={profile.company_info.sender_name}
                onChange={(e) =>
                  setProfile((p) => p && { ...p, company_info: { ...p.company_info, sender_name: e.target.value } })
                }
              />
            </Field>
          </div>
        </section>

        {/* ── Inventory Policy ────────────────────────────────────────── */}
        <section className="glass-card p-4">
          <div className="mb-3 font-mono text-[11px] font-semibold uppercase tracking-wide text-textMuted">
            Inventory Policy
          </div>
          <div className="grid grid-cols-3 gap-3">
            <Field label="Target Buffer (days)">
              <input
                className="glass-input"
                type="number"
                min={1}
                value={profile.inventory_policy.target_buffer_days}
                onChange={(e) =>
                  setProfile((p) => p && { ...p, inventory_policy: { ...p.inventory_policy, target_buffer_days: Number(e.target.value) } })
                }
              />
            </Field>
            <Field label="Reorder Threshold (days)">
              <input
                className="glass-input"
                type="number"
                min={1}
                value={profile.inventory_policy.reorder_threshold_days}
                onChange={(e) =>
                  setProfile((p) => p && { ...p, inventory_policy: { ...p.inventory_policy, reorder_threshold_days: Number(e.target.value) } })
                }
              />
            </Field>
            <Field label="Max Buffer (days)">
              <input
                className="glass-input"
                type="number"
                min={1}
                value={profile.inventory_policy.max_buffer_days}
                onChange={(e) =>
                  setProfile((p) => p && { ...p, inventory_policy: { ...p.inventory_policy, max_buffer_days: Number(e.target.value) } })
                }
              />
            </Field>
          </div>
        </section>

        {/* ── Suppliers ───────────────────────────────────────────────── */}
        <section className="glass-card p-4">
          <div className="mb-3 flex items-center justify-between">
            <span className="font-mono text-[11px] font-semibold uppercase tracking-wide text-textMuted">
              Suppliers ({profile.suppliers.length})
            </span>
            <button
              onClick={() => setSupplierModal({ supplier: { ...DEFAULT_SUPPLIER }, index: null })}
              className="flex items-center gap-1.5 rounded-md border border-accent/50 bg-accent/10 px-2.5 py-1.5 font-mono text-[11px] text-accent hover:bg-accent/20"
            >
              <PlusIcon className="h-3.5 w-3.5" />
              Add Supplier
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-[11px]">
              <thead>
                <tr className="border-b border-white/5 text-left font-mono text-[10px] uppercase tracking-wide text-textMuted">
                  <th className="pb-2 pr-3">ID</th>
                  <th className="pb-2 pr-3">Name</th>
                  <th className="pb-2 pr-3">Category</th>
                  <th className="pb-2 pr-3">Country</th>
                  <th className="pb-2 pr-3 text-right">Spend%</th>
                  <th className="pb-2 pr-3 text-right">Lead</th>
                  <th className="pb-2 pr-3 text-right">Health</th>
                  <th className="pb-2 pr-3">Single</th>
                  <th className="pb-2 pr-3">Contract</th>
                  <th className="pb-2" />
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {profile.suppliers.map((s, i) => (
                  <tr key={s.id} className="text-textPrimary">
                    <td className="py-2 pr-3 font-mono text-textMuted">{s.id}</td>
                    <td className="py-2 pr-3 font-medium">{s.name}</td>
                    <td className="py-2 pr-3 text-textMuted">{s.category}</td>
                    <td className="py-2 pr-3 text-textMuted">{s.country}</td>
                    <td className="py-2 pr-3 text-right font-mono">{s.spend_pct}%</td>
                    <td className="py-2 pr-3 text-right font-mono">{s.lead_time_days}d</td>
                    <td className="py-2 pr-3 text-right font-mono">
                      <span className={s.health_score >= 80 ? "text-success" : s.health_score >= 60 ? "text-warning" : "text-danger"}>
                        {s.health_score}
                      </span>
                    </td>
                    <td className="py-2 pr-3">
                      {s.single_source ? (
                        <span className="pill-high">Yes</span>
                      ) : (
                        <span className="text-textMuted">No</span>
                      )}
                    </td>
                    <td className="py-2 pr-3 font-mono text-textMuted">{s.contract_end}</td>
                    <td className="py-2">
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => setSupplierModal({ supplier: { ...s }, index: i })}
                          className="rounded p-1 text-textMuted hover:text-accent"
                        >
                          <EditIcon className="h-3.5 w-3.5" />
                        </button>
                        <button
                          onClick={() =>
                            setProfile((p) =>
                              p ? { ...p, suppliers: p.suppliers.filter((_, idx) => idx !== i) } : p
                            )
                          }
                          className="rounded p-1 text-textMuted hover:text-danger"
                        >
                          <TrashIcon className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* ── Customer SLAs ───────────────────────────────────────────── */}
        <section className="glass-card p-4">
          <div className="mb-3 flex items-center justify-between">
            <span className="font-mono text-[11px] font-semibold uppercase tracking-wide text-textMuted">
              Customer SLAs
            </span>
            <button
              onClick={() =>
                setProfile((p) =>
                  p ? { ...p, customer_slas: [...p.customer_slas, { ...DEFAULT_SLA }] } : p
                )
              }
              className="flex items-center gap-1.5 rounded-md border border-accent/50 bg-accent/10 px-2.5 py-1.5 font-mono text-[11px] text-accent hover:bg-accent/20"
            >
              <PlusIcon className="h-3.5 w-3.5" />
              Add SLA
            </button>
          </div>
          <div className="space-y-2">
            {profile.customer_slas.map((sla, i) => (
              <div key={i} className="grid grid-cols-12 items-center gap-2 rounded-lg border border-white/5 bg-surfaceMuted px-3 py-2">
                <div className="col-span-4">
                  <Field label="Customer">
                    <input
                      className="glass-input"
                      value={sla.customer}
                      onChange={(e) =>
                        setProfile((p) =>
                          p
                            ? { ...p, customer_slas: p.customer_slas.map((s, idx) => idx === i ? { ...s, customer: e.target.value } : s) }
                            : p
                        )
                      }
                    />
                  </Field>
                </div>
                <div className="col-span-3">
                  <Field label="On-Time Delivery %">
                    <input
                      className="glass-input"
                      type="number"
                      min={0}
                      max={100}
                      step={0.1}
                      value={sla.on_time_delivery_pct}
                      onChange={(e) =>
                        setProfile((p) =>
                          p
                            ? { ...p, customer_slas: p.customer_slas.map((s, idx) => idx === i ? { ...s, on_time_delivery_pct: Number(e.target.value) } : s) }
                            : p
                        )
                      }
                    />
                  </Field>
                </div>
                <div className="col-span-4">
                  <Field label="Penalty / Day (USD)">
                    <input
                      className="glass-input"
                      type="number"
                      min={0}
                      value={sla.penalty_per_day_usd}
                      onChange={(e) =>
                        setProfile((p) =>
                          p
                            ? { ...p, customer_slas: p.customer_slas.map((s, idx) => idx === i ? { ...s, penalty_per_day_usd: Number(e.target.value) } : s) }
                            : p
                        )
                      }
                    />
                  </Field>
                </div>
                <div className="col-span-1 flex items-end pb-0.5">
                  <button
                    onClick={() =>
                      setProfile((p) =>
                        p ? { ...p, customer_slas: p.customer_slas.filter((_, idx) => idx !== i) } : p
                      )
                    }
                    className="rounded p-1 text-textMuted hover:text-danger"
                  >
                    <TrashIcon className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* ── Production Lines ────────────────────────────────────────── */}
        <section className="glass-card p-4">
          <div className="mb-3 flex items-center justify-between">
            <span className="font-mono text-[11px] font-semibold uppercase tracking-wide text-textMuted">
              Production Lines
            </span>
            <button
              onClick={() =>
                setProfile((p) =>
                  p ? { ...p, production_lines: [...p.production_lines, { ...DEFAULT_LINE }] } : p
                )
              }
              className="flex items-center gap-1.5 rounded-md border border-accent/50 bg-accent/10 px-2.5 py-1.5 font-mono text-[11px] text-accent hover:bg-accent/20"
            >
              <PlusIcon className="h-3.5 w-3.5" />
              Add Line
            </button>
          </div>
          <div className="space-y-2">
            {profile.production_lines.map((line, i) => (
              <div key={i} className="grid grid-cols-12 items-center gap-2 rounded-lg border border-white/5 bg-surfaceMuted px-3 py-2">
                <div className="col-span-2">
                  <Field label="Line ID">
                    <input
                      className="glass-input"
                      value={line.line_id}
                      onChange={(e) =>
                        setProfile((p) =>
                          p ? { ...p, production_lines: p.production_lines.map((l, idx) => idx === i ? { ...l, line_id: e.target.value } : l) } : p
                        )
                      }
                    />
                  </Field>
                </div>
                <div className="col-span-3">
                  <Field label="Product">
                    <input
                      className="glass-input"
                      value={line.product}
                      onChange={(e) =>
                        setProfile((p) =>
                          p ? { ...p, production_lines: p.production_lines.map((l, idx) => idx === i ? { ...l, product: e.target.value } : l) } : p
                        )
                      }
                    />
                  </Field>
                </div>
                <div className="col-span-2">
                  <Field label="Daily Output">
                    <input
                      className="glass-input"
                      type="number"
                      min={0}
                      value={line.daily_output_units}
                      onChange={(e) =>
                        setProfile((p) =>
                          p ? { ...p, production_lines: p.production_lines.map((l, idx) => idx === i ? { ...l, daily_output_units: Number(e.target.value) } : l) } : p
                        )
                      }
                    />
                  </Field>
                </div>
                <div className="col-span-2">
                  <Field label="Daily Revenue ($)">
                    <input
                      className="glass-input"
                      type="number"
                      min={0}
                      value={line.daily_revenue_usd}
                      onChange={(e) =>
                        setProfile((p) =>
                          p ? { ...p, production_lines: p.production_lines.map((l, idx) => idx === i ? { ...l, daily_revenue_usd: Number(e.target.value) } : l) } : p
                        )
                      }
                    />
                  </Field>
                </div>
                <div className="col-span-2 flex items-end gap-2 pb-0.5">
                  <button
                    type="button"
                    role="switch"
                    aria-checked={line.semiconductor_dependent}
                    onClick={() =>
                      setProfile((p) =>
                        p ? { ...p, production_lines: p.production_lines.map((l, idx) => idx === i ? { ...l, semiconductor_dependent: !l.semiconductor_dependent } : l) } : p
                      )
                    }
                    className={`relative inline-flex h-5 w-9 shrink-0 rounded-full transition-colors ${line.semiconductor_dependent ? "bg-accent" : "bg-surface"}`}
                  >
                    <span className={`pointer-events-none inline-block h-4 w-4 translate-y-0.5 rounded-full bg-white shadow transition-transform ${line.semiconductor_dependent ? "translate-x-5" : "translate-x-0.5"}`} />
                  </button>
                  <span className="text-[10px] text-textMuted leading-tight">Semi-dep.</span>
                </div>
                <div className="col-span-1 flex items-end pb-0.5">
                  <button
                    onClick={() =>
                      setProfile((p) =>
                        p ? { ...p, production_lines: p.production_lines.filter((_, idx) => idx !== i) } : p
                      )
                    }
                    className="rounded p-1 text-textMuted hover:text-danger"
                  >
                    <TrashIcon className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* ── Disruption Simulation ───────────────────────────────────── */}
        <section className="glass-card p-4">
          <div className="mb-3 flex items-center gap-2 font-mono text-[11px] font-semibold uppercase tracking-wide text-textMuted">
            <BoltIcon className="h-4 w-4 text-warning" />
            Disruption Simulation
          </div>
          <p className="mb-4 text-[11px] text-textMuted">
            Inject a shipping lane disruption into the system for demo or testing. The agent pipeline will detect and respond to it on the next run.
          </p>
          <div className="flex flex-wrap items-end gap-4">
            <div className="flex flex-col gap-1">
              <label className="font-mono text-[10px] uppercase tracking-wider text-textMuted">Shipping Lane</label>
              <select
                className="glass-input min-w-[220px]"
                value={simLane}
                onChange={(e) => setSimLane(e.target.value)}
              >
                {LANE_OPTIONS.map((l) => (
                  <option key={l} value={l}>{l}</option>
                ))}
              </select>
            </div>
            <div className="flex flex-col gap-1">
              <label className="font-mono text-[10px] uppercase tracking-wider text-textMuted">
                Delay Days: <span className="text-textPrimary">{simDelay}</span>
              </label>
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min={1}
                  max={30}
                  value={simDelay}
                  onChange={(e) => setSimDelay(Number(e.target.value))}
                  className="glass-slider w-32"
                />
                <span className="font-mono text-sm font-semibold text-textPrimary">{simDelay}d</span>
              </div>
            </div>
            <div className="flex items-end gap-2">
              <button
                onClick={handleInitiate}
                disabled={simStatus === "loading"}
                className="flex items-center gap-2 rounded-lg bg-warning/90 px-4 py-2 font-mono text-xs font-semibold text-black hover:bg-warning disabled:opacity-60"
              >
                <BoltIcon className="h-3.5 w-3.5" />
                {simStatus === "loading" ? "Working…" : "Initiate Disruption"}
              </button>
              <button
                onClick={handleClear}
                disabled={simStatus === "loading"}
                className="rounded-lg border border-white/10 bg-surfaceMuted px-4 py-2 font-mono text-xs text-textMuted hover:text-textPrimary disabled:opacity-60"
              >
                Clear Disruption
              </button>
            </div>
          </div>
          {simMessage && (
            <p className={`mt-3 font-mono text-[11px] ${simStatus === "error" ? "text-danger" : "text-success"}`}>
              {simMessage}
            </p>
          )}
        </section>
      </div>

      {supplierModal && (
        <SupplierModal
          supplier={supplierModal.supplier}
          onSave={(updated) => {
            setProfile((p) => {
              if (!p) return p;
              if (supplierModal.index === null) {
                return { ...p, suppliers: [...p.suppliers, updated] };
              }
              return {
                ...p,
                suppliers: p.suppliers.map((s, i) => (i === supplierModal.index ? updated : s)),
              };
            });
            setSupplierModal(null);
          }}
          onClose={() => setSupplierModal(null)}
        />
      )}
    </LayoutShell>
  );
}
