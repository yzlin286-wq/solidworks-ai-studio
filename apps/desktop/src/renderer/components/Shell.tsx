import { ClipboardText, Command, GearSix, Graph, House, Network, Stack, Wrench } from "@phosphor-icons/react";
import type { ReactNode } from "react";
import type { HealthResponse, MCPStatusResponse, PreflightResponse, TestConnectionResponse, ViewKey } from "../lib/types";
import { preflightBadgeStatus, preflightStatusLabel, zhCN } from "../lib/copy/zhCN";
import { StatusBadge } from "./StatusBadge";

interface ShellProps {
  view: ViewKey;
  onNavigate: (view: ViewKey) => void;
  health: HealthResponse | null;
  llmConnection: TestConnectionResponse | null;
  preflight: PreflightResponse | null;
  mcp: MCPStatusResponse | null;
  onPaletteOpen: () => void;
  children: ReactNode;
}

const navItems = [
  { view: "dashboard" as const, label: "Dashboard", icon: House },
  { view: "capabilities" as const, label: "Capabilities", icon: Stack },
  { view: "tasks" as const, label: "Tasks", icon: ClipboardText },
  { view: "integration" as const, label: "Integration", icon: Network },
  { view: "developer" as const, label: "Developer", icon: Wrench },
  { view: "settings" as const, label: "Settings", icon: GearSix }
];

export function Shell({ view, onNavigate, health, llmConnection, preflight, mcp, onPaletteOpen, children }: ShellProps) {
  const llmVerified = Boolean(llmConnection?.ok && llmConnection.chat_verified);
  return (
    <div className="app-shell">
      <a href="#main-content" className="skip-link">{zhCN.shell.skipToContent}</a>
      <aside className="nav-rail" aria-label={zhCN.shell.navigation}>
        <div className="brand-mark" aria-label={zhCN.appName}>
          <Graph size={24} weight="duotone" />
        </div>
        <nav>
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = view === item.view;
            return (
              <button
                key={item.view}
                type="button"
                className={active ? "nav-button active" : "nav-button"}
                onClick={() => onNavigate(item.view)}
                title={item.label}
                aria-current={active ? "page" : undefined}
              >
                <Icon size={22} weight="duotone" aria-hidden />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
        <button type="button" className="palette-button" onClick={onPaletteOpen}>
          <Command size={19} weight="duotone" aria-hidden />
          <span>{zhCN.shell.paletteShortcut}</span>
        </button>
      </aside>

      <div className="work-surface">
        <header className="top-bar">
          <div>
            <p className="eyebrow">{zhCN.appName}</p>
            <h1>{titleForView(view)}</h1>
          </div>
          <div className="top-status" aria-label={zhCN.shell.systemStatus}>
            <StatusBadge status={health?.ok ? "pass" : "warn"} label={health?.ok ? zhCN.shell.statuses.apiOnline : zhCN.shell.statuses.apiPending} />
            <StatusBadge status={llmVerified ? "pass" : "warn"} label={llmVerified ? zhCN.shell.statuses.llmVerified : zhCN.shell.statuses.llmUnverified} />
            <StatusBadge status={preflightBadgeStatus(preflight)} label={preflightStatusLabel(preflight)} />
            <StatusBadge status={mcp?.running ? "pass" : "info"} label={mcp?.running ? zhCN.shell.statuses.mcpRunning : zhCN.shell.statuses.mcpStopped} />
          </div>
        </header>
        <main id="main-content" className="main-content" tabIndex={-1}>
          {children}
        </main>
      </div>
    </div>
  );
}

function titleForView(view: ViewKey): string {
  const titles: Record<ViewKey, string> = {
    dashboard: "Dashboard",
    capabilities: "AI Capability Workbench",
    tasks: "Task History",
    integration: "Integration",
    developer: "Developer",
    settings: zhCN.viewTitles.settings
  };
  return titles[view];
}
