import type { ReactNode } from "react";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

export function LayoutShell({
  title,
  subtitle,
  lastSync,
  headerRight,
  children,
}: {
  title: string;
  subtitle?: string;
  lastSync?: string;
  headerRight?: React.ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="flex h-screen overflow-hidden bg-background text-textPrimary">
      <Sidebar />
      <div className="flex min-h-0 flex-1 flex-col">
        <Topbar title={title} subtitle={subtitle} lastSync={lastSync} headerRight={headerRight} />
        <main className="flex flex-1 min-h-0 flex-col bg-background px-6 py-4 overflow-hidden">
          {children}
        </main>
      </div>
    </div>
  );
}

