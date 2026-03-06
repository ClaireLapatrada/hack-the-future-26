"use client";

import { useState, useEffect } from "react";

export function Topbar({
  title,
  subtitle,
  lastSync,
  headerRight,
}: {
  title: string;
  subtitle?: string;
  lastSync?: string;
  headerRight?: React.ReactNode;
}) {
    const [now, setNow] = useState<Date | null>(null);

  useEffect(() => {
    setNow(new Date());
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  const dateStr = now
    ? now.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" })
    : "—";
  const timeStr = now
    ? now.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: true })
    : "—";
  return (
    <>
      {/* Top bar: date/time + ADK Agent Online pill */}
      <div className="flex items-center justify-between border-b border-white/5 bg-topBar px-6 py-2.5">
        <div className="flex items-center gap-3">
          <LayoutIcon className="h-4 w-4 shrink-0 text-textMuted" />
          <div className="flex flex-col font-mono text-sm text-textPrimary leading-tight">
            <span>{dateStr}</span>
            <span className="text-xs text-textMuted">{timeStr}</span>
          </div>
        </div>
        <div className="flex items-center gap-2 rounded-lg border border-agentCyan/50 bg-surfaceMuted/80 px-3 py-1.5">
          <span className="h-1.5 w-1.5 shrink-0 rounded-md bg-agentCyan" />
          <AgentIcon className="h-3.5 w-3.5 shrink-0 text-agentCyan" />
          <span className="font-mono text-xs font-medium text-agentCyan">
            ADK Agent Online
          </span>
        </div>
      </div>
      {/* Header: page title (and optional subtitle + last sync or custom right content) under the top bar */}
      <header className="flex min-h-[3.5rem] items-center justify-between overflow-visible border-b border-white/5 bg-surface px-6 py-3">
        <div>
          <h1 className="text-lg font-semibold">{title}</h1>
          {subtitle && (
            <p className="mt-0.5 font-mono text-sm text-textMuted">{subtitle}</p>
          )}
        </div>
        {headerRight != null ? (
          <div className="flex shrink-0 items-center overflow-visible">{headerRight}</div>
        ) : lastSync != null ? (
          <div className="flex items-center gap-2 font-mono text-sm text-textPrimary">
            <ClockIcon className="h-4 w-4 text-textMuted" />
            <span>Last sync: {lastSync}</span>
          </div>
        ) : null}
      </header>
    </>
  );
}

function LayoutIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 16 16"
      fill="currentColor"
      aria-hidden
    >
      <rect x="1" y="2" width="5" height="12" rx="0.5" />
      <rect x="7.5" y="2" width="1" height="12" rx="0.25" />
      <rect x="10" y="2" width="5" height="12" rx="0.5" />
    </svg>
  );
}

function AgentIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 16 16"
      fill="currentColor"
      aria-hidden
    >
      <ellipse cx="8" cy="10" rx="4" ry="3" />
      <rect x="6" y="4" width="4" height="4" rx="1" />
      <circle cx="7" cy="6.5" r="0.6" />
      <circle cx="9" cy="6.5" r="0.6" />
      <path d="M8 2 L8 0 M5.5 1.5 L4.5 0.5 M10.5 1.5 L11.5 0.5" stroke="currentColor" strokeWidth="0.8" fill="none" />
    </svg>
  );
}

function ClockIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden>
      <circle cx="8" cy="8" r="6" />
      <path d="M8 4v4l2.5 2.5" />
    </svg>
  );
}
