"use client";

import { useState, useEffect } from "react";
import { LayoutShell } from "../../components/LayoutShell";

function BoxIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor" aria-hidden>
      <path
        fillRule="evenodd"
        d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zm0 6a1 1 0 011-1h12a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6zm2 2a1 1 0 011-1h6a1 1 0 011 1v2a1 1 0 01-1 1H7a1 1 0 01-1-1v-2z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function UserIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor" aria-hidden>
      <path
        fillRule="evenodd"
        d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function RefreshIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor" aria-hidden>
      <path
        fillRule="evenodd"
        d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885c-.627-.95-1.608-1.74-2.732-2.256V3a1 1 0 011-1h2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885A9.002 9.002 0 003 5V3a1 1 0 011-1h2z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function SaveIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor" aria-hidden>
      <path
        fillRule="evenodd"
        d="M3 4a1 1 0 011-1h12a1 1 0 011 1v12a1 1 0 01-1 1H4a1 1 0 01-1-1V4zm2 2a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H7a1 1 0 01-1-1V6z"
        clipRule="evenodd"
      />
    </svg>
  );
}

type SliderRule = {
  type: "slider";
  name: string;
  description: string;
  min: number;
  max: number;
  unit: string;
  key: string;
};
type InputRule = {
  type: "input";
  name: string;
  description: string;
  key: string;
};
type ToggleRule = {
  type: "toggle";
  name: string;
  description: string;
  key: string;
};

type Rule = SliderRule | InputRule | ToggleRule;

type RulesConfig = {
  sections: Array<{ group: string; icon: "box" | "user"; rules: Rule[] }>;
  initialValues: Record<string, number | string | boolean>;
};

const DEFAULT_VALUES: Record<string, number | string | boolean> = {
  globalThreshold: 75,
  revenueThreshold: "$2,000,000",
  autoSafetyStock: true,
  escalationWindow: 15,
  multiSupplierEscalate: true,
  offHoursEscalation: false,
  approvalTimeout: 50,
  dualApprovalCritical: true,
  agentAutoApproveLow: false,
};

export default function RulesPage() {
  const [config, setConfig] = useState<RulesConfig | null>(null);
  const [values, setValues] = useState<Record<string, number | string | boolean>>(DEFAULT_VALUES);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saveStatus, setSaveStatus] = useState<"idle" | "saving" | "saved" | "error">("idle");

  useEffect(() => {
    fetch("/api/rules")
      .then((res) => {
        if (!res.ok) throw new Error("Failed to load rules");
        return res.json();
      })
      .then((data: RulesConfig) => {
        setConfig(data);
        setValues(data.initialValues ?? DEFAULT_VALUES);
      })
      .catch((e) => setLoadError(e instanceof Error ? e.message : "Failed to load"));
  }, []);

  const ruleSections = config?.sections ?? [];
  const initialValues = config?.initialValues ?? DEFAULT_VALUES;

  const handleSliderChange = (key: string, v: number) => setValues((prev) => ({ ...prev, [key]: v }));
  const handleInputChange = (key: string, v: string) => setValues((prev) => ({ ...prev, [key]: v }));
  const handleToggleChange = (key: string) =>
    setValues((prev) => ({ ...prev, [key]: !prev[key] }));

  const handleReset = async () => {
    try {
      const res = await fetch("/api/rules");
      if (!res.ok) throw new Error("Failed to load");
      const data = (await res.json()) as RulesConfig;
      setConfig(data);
      setValues({ ...(data.initialValues ?? DEFAULT_VALUES) });
    } catch {
      setValues({ ...DEFAULT_VALUES });
    }
  };

  const handleSave = async () => {
    setSaveStatus("saving");
    try {
      const res = await fetch("/api/rules", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ initialValues: values }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || "Failed to save");
      }
      const data = (await res.json()) as RulesConfig;
      setConfig(data);
      setValues(data.initialValues ?? values);
      setSaveStatus("saved");
      setTimeout(() => setSaveStatus("idle"), 2000);
    } catch (e) {
      setSaveStatus("error");
      setTimeout(() => setSaveStatus("idle"), 3000);
    }
  };

  const headerActions = (
    <div className="flex items-center gap-2 overflow-visible">
      <button
        onClick={handleReset}
        className="flex min-w-0 items-center justify-center gap-2 overflow-visible rounded-lg border border-white/10 bg-surfaceMuted pl-3.5 pr-3 py-2 font-mono text-xs text-textMuted transition hover:border-white/20 hover:text-textPrimary"
      >
        <RefreshIcon className="h-3.5 w-3.5 shrink-0" />
        Reset
      </button>
      <button
        onClick={handleSave}
        disabled={saveStatus === "saving"}
        className="flex min-w-0 items-center gap-2 rounded-lg bg-accent px-4 py-2 font-mono text-xs font-semibold text-black transition hover:bg-accentSoft disabled:opacity-60"
      >
        <SaveIcon className="h-3.5 w-3.5 shrink-0" />
        {saveStatus === "saving" ? "Saving…" : saveStatus === "saved" ? "Saved" : "Save Changes"}
      </button>
      {saveStatus === "error" && (
        <span className="text-xs text-danger">Save failed</span>
      )}
    </div>
  );

  return (
    <LayoutShell
      title="Rules & Thresholds"
      subtitle="Configure agent behavior, risk appetite, and supply chain escalation policies"
      headerRight={headerActions}
    >
      <div className="flex h-full min-h-0 flex-col">
        {loadError && (
          <div className="mb-3 rounded-lg border border-danger/50 bg-danger/10 px-4 py-2 text-xs text-danger">
            {loadError}
          </div>
        )}
        <div className="min-h-0 flex-1 space-y-4 overflow-y-auto text-xs">
          {ruleSections.map((section) => (
            <section key={section.group} className="glass-card p-4">
              <div className="mb-3 flex items-center gap-2 text-[11px] font-semibold text-textMuted">
                {section.icon === "box" ? (
                  <BoxIcon className="h-4 w-4" />
                ) : (
                  <UserIcon className="h-4 w-4" />
                )}
                {section.group}
              </div>
              <div className="space-y-4">
                {section.rules.map((rule) => (
                  <div
                    key={rule.key}
                    className="flex flex-col gap-2 rounded-lg border border-white/5 bg-surfaceMuted px-3 py-3 sm:flex-row sm:items-center sm:justify-between"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="text-xs font-medium text-textPrimary">
                        {rule.name}
                      </div>
                      <div className="mt-0.5 text-[11px] text-textMuted">
                        {rule.description}
                      </div>
                    </div>
                    <div className="flex shrink-0 items-center gap-3">
                      {rule.type === "slider" && (
                        <>
                          <input
                            type="range"
                            min={rule.min}
                            max={rule.max}
                            value={Number(values[rule.key] ?? rule.min)}
                            onChange={(e) =>
                              handleSliderChange(rule.key, Number(e.target.value))
                            }
                            className="glass-slider"
                          />
                          <span className="font-mono text-[11px] font-semibold text-textPrimary">
                            {values[rule.key]}
                            {rule.unit}
                          </span>
                        </>
                      )}
                      {rule.type === "input" && (
                        <input
                          type="text"
                          value={String(values[rule.key] ?? "")}
                          onChange={(e) => handleInputChange(rule.key, e.target.value)}
                          className="glass-input w-36"
                        />
                      )}
                      {rule.type === "toggle" && (
                        <button
                          type="button"
                          role="switch"
                          aria-checked={Boolean(values[rule.key])}
                          onClick={() => handleToggleChange(rule.key)}
                          className={`relative inline-flex h-6 w-11 shrink-0 rounded-full transition-colors ${
                            values[rule.key] ? "bg-accent" : "bg-surface"
                          }`}
                        >
                          <span
                            className={`pointer-events-none inline-block h-5 w-5 translate-y-0.5 rounded-full bg-white shadow transition-transform ${
                              values[rule.key] ? "translate-x-6" : "translate-x-0.5"
                            }`}
                          />
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </section>
          ))}

          <section className="glass-card p-4 text-[11px] text-textMuted">
            <div className="mb-1 text-xs font-semibold text-textPrimary">
              Agent Configuration Note
            </div>
            <p>
              Changes to rules are validated by the ADK agent before deployment.
              The agent will simulate the impact of rule changes on the last 90
              days of supply chain disruption data and flag any configurations
              that would have caused missed disruptions or unnecessary
              escalations.
            </p>
          </section>
        </div>
      </div>
    </LayoutShell>
  );
}
