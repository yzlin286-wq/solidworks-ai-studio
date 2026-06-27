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

const commands: ReadonlyArray<{ label: string; hint: string; view?: ViewKey; action?: "refresh" }> = [
  { label: "打开 Dashboard", hint: "查看能力、Recipe 和任务概览", view: "dashboard" },
  { label: "打开 Capabilities", hint: "进入 AI workflow grouped sidebar", view: "capabilities" },
  { label: "打开 Task History", hint: "查看 artifacts 和执行记录", view: "tasks" },
  { label: "打开 Integration", hint: "Direct Tools / MCP / Developer 区域", view: "integration" },
  { label: "打开 Settings", hint: "配置 LLM Provider 和本地后端", view: "settings" },
  { label: "刷新", hint: "重新读取后端状态", action: "refresh" }
];

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
