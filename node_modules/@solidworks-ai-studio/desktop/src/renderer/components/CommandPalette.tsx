import { Command, MagnifyingGlass } from "@phosphor-icons/react";
import { useEffect, useMemo, useState } from "react";
import type { ViewKey } from "../lib/types";
import { zhCN } from "../lib/copy/zhCN";

interface CommandPaletteProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onNavigate: (view: ViewKey) => void;
  onRefresh: () => void;
}

const commands = zhCN.palette.commands as ReadonlyArray<{ label: string; hint: string; view?: ViewKey; action?: "refresh" }>;

export function CommandPalette({ open, onOpenChange, onNavigate, onRefresh }: CommandPaletteProps) {
  const [query, setQuery] = useState("");

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        onOpenChange(!open);
      }
      if (event.key === "Escape") {
        onOpenChange(false);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onOpenChange, open]);

  const filtered = useMemo(
    () => commands.filter((item) => `${item.label} ${item.hint}`.toLowerCase().includes(query.toLowerCase())),
    [query]
  );

  if (!open) {
    return null;
  }

  return (
    <div className="command-backdrop" role="presentation" onMouseDown={() => onOpenChange(false)}>
      <div className="command-panel" role="dialog" aria-modal="true" aria-label={zhCN.palette.ariaLabel} onMouseDown={(event) => event.stopPropagation()}>
        <div className="command-search">
          <MagnifyingGlass size={18} aria-hidden />
          <input autoFocus value={query} onChange={(event) => setQuery(event.target.value)} placeholder={zhCN.palette.placeholder} />
          <span><Command size={14} aria-hidden /> K</span>
        </div>
        <div className="command-list">
          {filtered.map((item) => (
            <button
              key={item.label}
              type="button"
              onClick={() => {
                if (item.view) {
                  onNavigate(item.view);
                }
                if (item.action === "refresh") {
                  onRefresh();
                }
                onOpenChange(false);
              }}
            >
              <strong>{item.label}</strong>
              <span>{item.hint}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
