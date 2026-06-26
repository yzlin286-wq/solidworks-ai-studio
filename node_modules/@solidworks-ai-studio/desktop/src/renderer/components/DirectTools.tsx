import {
  ArrowLineDown,
  Cube,
  FilePlus,
  FloppyDisk,
  FolderOpen,
  Link,
  MagnifyingGlass,
  PlugsConnected,
  Pulse,
  RocketLaunch
} from "@phosphor-icons/react";
import type { SolidWorksActionResponse } from "../lib/types";
import type { Capability } from "../lib/types";
import { modeLabel, realValidationStatusLabel, zhCN } from "../lib/copy/zhCN";

interface DirectToolsProps {
  busy: boolean;
  lastAction: SolidWorksActionResponse | null;
  capabilities: Capability[];
  onTool: (tool: string) => Promise<void>;
  onCapabilityRun: (capabilityId: string) => Promise<void>;
}

const tools = [
  { key: "health", label: zhCN.tools.items.health, icon: Pulse },
  { key: "connect", label: zhCN.tools.items.connect, icon: PlugsConnected },
  { key: "new-part", label: zhCN.tools.items.newPart, icon: FilePlus },
  { key: "open", label: zhCN.tools.items.open, icon: FolderOpen },
  { key: "save", label: zhCN.tools.items.save, icon: FloppyDisk },
  { key: "export-step", label: zhCN.tools.items.exportStep, icon: ArrowLineDown },
  { key: "export-stl", label: zhCN.tools.items.exportStl, icon: ArrowLineDown },
  { key: "export-pdf", label: zhCN.tools.items.exportPdf, icon: ArrowLineDown },
  { key: "export-dxf", label: zhCN.tools.items.exportDxf, icon: ArrowLineDown },
  { key: "export-dwg", label: zhCN.tools.items.exportDwg, icon: ArrowLineDown },
  { key: "review", label: zhCN.tools.items.review, icon: MagnifyingGlass },
  { key: "create-basic-part", label: zhCN.tools.items.createBasicPart, icon: Cube },
  { key: "mcp-start", label: zhCN.tools.items.mcpStart, icon: RocketLaunch },
  { key: "mcp-stop", label: zhCN.tools.items.mcpStop, icon: Link }
];

const registryToolOrder: Record<string, number> = {
  "mcp.solidworks_connect": 10,
  "mcp.solidworks_health_check": 20,
  "mcp.solidworks_create_basic_part": 30,
  "mcp.solidworks_new_document": 40,
  "mcp.solidworks_open_document": 50,
  "mcp.solidworks_save_document": 60,
  "mcp.solidworks_export_active": 70,
  "mcp.solidworks_review_active": 80,
  "mcp.solidworks_set_appearance": 90,
  "mcp.solidworks_add_component": 100,
  "mcp.solidworks_set_component_fixed": 110,
  "mcp.solidworks_add_coincident_mate": 120,
  "mcp.solidworks_add_distance_mate": 130,
  "mcp.solidworks_add_concentric_mate": 140,
  "mcp.solidworks_close_documents": 900,
  "mcp.solidworks_add_rotary_motor": 990
};

export function DirectTools({ busy, lastAction, capabilities, onTool, onCapabilityRun }: DirectToolsProps) {
  const dynamicTools = capabilities
    .filter((capability) => capability.callable && capability.ui_exposed && capability.execution_kind === "mcp_tool")
    .sort((left, right) => (registryToolOrder[left.id] ?? 500) - (registryToolOrder[right.id] ?? 500) || left.title.localeCompare(right.title, "zh-CN"))
    .slice(0, 18);
  return (
    <section className="direct-tools-panel" aria-labelledby="direct-tools-title">
      <div className="panel-heading compact">
        <div>
          <p className="eyebrow">{zhCN.tools.eyebrow}</p>
          <h2 id="direct-tools-title">{zhCN.tools.title}</h2>
        </div>
      </div>
      <div className="tool-grid">
        {tools.map((tool) => {
          const Icon = tool.icon;
          return (
            <button key={tool.key} type="button" disabled={busy} onClick={() => onTool(tool.key)}>
              <Icon size={19} weight="duotone" aria-hidden />
              {tool.label}
            </button>
          );
        })}
      </div>
      <div className="registry-tool-list" aria-label="能力 Registry 工具">
        <h3>{zhCN.tools.registryTitle}</h3>
        {dynamicTools.map((capability) => (
          <button key={capability.id} type="button" disabled={busy} onClick={() => onCapabilityRun(capability.id)}>
            <RocketLaunch size={17} weight="duotone" aria-hidden />
            <span>{capability.title}</span>
            <small>{realValidationStatusLabel(capability.real_sw2025_status)}</small>
          </button>
        ))}
      </div>
      <div className="tool-result" aria-live="polite">
        <h3>{zhCN.tools.lastAction}</h3>
        {lastAction ? (
          <>
            <strong>{lastAction.action}</strong>
            <p>{lastAction.message}</p>
            <span>{modeLabel(lastAction.mode)} {zhCN.tools.mode}</span>
            <div className="evidence-panel compact">
              <strong>{zhCN.tools.realEvidence}: {lastAction.real_execution_verified ? zhCN.tools.verified : zhCN.tools.unverified}</strong>
              <small>before: {lastAction.active_document_before || "未记录"}</small>
              <small>after: {lastAction.active_document_after || "未记录"}</small>
              <small>files: {lastAction.files.length} / exist: {lastAction.created_files_exist ? "true" : "false"}</small>
            </div>
          </>
        ) : (
          <p className="muted-copy">{zhCN.tools.noAction}</p>
        )}
      </div>
    </section>
  );
}
