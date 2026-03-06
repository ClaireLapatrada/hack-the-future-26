"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/", label: "Dashboard", icon: "dashboard" },
  { href: "/disruptions", label: "Disruptions", icon: "disruptions" },
  { href: "/approvals", label: "Approvals", icon: "approvals" },
  { href: "/rules", label: "Rules", icon: "rules" },
] as const;

function LogoIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden
    >
      {/* Cargo / container ship style */}
      <path d="M20 6h-2V4c0-1.1-.9-2-2-2H8c-1.1 0-2 .9-2 2v2H4c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2zm-10-2h4v2h-4V4zm8 14H6V8h12v10z" />
      <path d="M10 11h4v2h-4z" />
    </svg>
  );
}

function DashboardIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor" aria-hidden>
      <path d="M3 4a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 14a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1H4a1 1 0 01-1-1v-4zM13 4a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1V4zM13 14a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" />
    </svg>
  );
}

function DisruptionsIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor" aria-hidden>
      <path
        fillRule="evenodd"
        d="M4 4a2 2 0 00-2 2v6a2 2 0 002 2h2v2a1 1 0 102 0v-2h4v2a1 1 0 102 0v-2h2a2 2 0 002-2V6a2 2 0 00-2-2H4.586L10 8.586 6.414 5H4zm6 6a1 1 0 10-2 0v3.586L7.707 11.293a1 1 0 00-1.414 1.414l3 3a1 1 0 001.414 0l3-3a1 1 0 00-1.414-1.414L10 13.586V10z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function ApprovalsIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor" aria-hidden>
      <path d="M2.003 5.884L10 9.882l7.997-3.998A2 2 0 0016 4H4a2 2 0 00-1.997 1.884z" />
      <path d="M18 8.118l-8 4-8-4V14a2 2 0 002 2h12a2 2 0 002-2V8.118z" />
    </svg>
  );
}

function RulesIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor" aria-hidden>
      <path
        fillRule="evenodd"
        d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z"
        clipRule="evenodd"
      />
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

function NavIcon({ icon }: { icon: (typeof NAV_ITEMS)[number]["icon"] }) {
  switch (icon) {
    case "dashboard":
      return <DashboardIcon className="h-5 w-5 shrink-0" />;
    case "disruptions":
      return <DisruptionsIcon className="h-5 w-5 shrink-0" />;
    case "approvals":
      return <ApprovalsIcon className="h-5 w-5 shrink-0" />;
    case "rules":
      return <RulesIcon className="h-5 w-5 shrink-0" />;
  }
}

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex h-full w-64 flex-col border-r border-white/5 bg-sidebar px-4 py-5">
      {/* Branding */}
      <div className="mb-8 flex items-center gap-3 px-2">
        <LogoIcon className="h-8 w-8 shrink-0 text-accent" />
        <div className="flex min-w-0 flex-col">
          <span className="text-sm font-bold uppercase tracking-tight text-textPrimary">
            CHAINGUARD
          </span>
          <span className="font-mono text-[10px] uppercase tracking-wider text-textMuted">
            Supply Chain Intelligence
          </span>
        </div>
      </div>

      {/* Nav section */}
      <nav className="flex flex-1 flex-col">
        <div className="mb-2 px-3 font-mono text-[10px] font-medium uppercase tracking-wider text-textMuted">
          Supply Ops
        </div>
        <div className="space-y-0.5">
          {NAV_ITEMS.map((item) => {
            const active =
              item.href === "/"
                ? pathname === "/"
                : pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`relative flex items-center gap-3 rounded-r-lg py-2.5 transition ${
                  active
                    ? "bg-accent/25 pl-4 pr-3 text-accent"
                    : "px-3 text-textPrimary hover:bg-surfaceMuted/80 hover:text-textPrimary"
                }`}
              >
                {active && (
                  <span
                    className="absolute left-0 top-0 h-full w-1 rounded-r-full bg-accent"
                    aria-hidden
                  />
                )}
                <NavIcon icon={item.icon} />
                <span className="text-sm font-medium">{item.label}</span>
              </Link>
            );
          })}
        </div>
      </nav>

      {/* Agent status */}
      <div className="mt-auto flex items-center gap-2 rounded-lg border border-agentCyan/50 bg-transparent px-3 py-2">
        <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-agentCyan" />
        <AgentIcon className="h-3.5 w-3.5 shrink-0 text-agentCyan" />
        <span className="font-mono text-xs font-medium text-agentCyan">
          ADK Agent Online
        </span>
      </div>
    </aside>
  );
}
