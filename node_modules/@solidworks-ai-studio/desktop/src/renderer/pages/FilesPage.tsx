import { Archive, FolderOpen } from "@phosphor-icons/react";
import type { RunRecord, SolidWorksActionResponse } from "../lib/types";
import { zhCN } from "../lib/copy/zhCN";

interface FilesPageProps {
  run: RunRecord | null;
  lastAction: SolidWorksActionResponse | null;
}

export function FilesPage({ run, lastAction }: FilesPageProps) {
  const files = Array.from(new Set([...(run?.files ?? []), ...(lastAction?.files ?? [])]));
  const groups = [".sldprt", ".sldasm", ".step", ".stp", ".stl", ".pdf", ".dxf", ".dwg", ".json", ".bmp", ".png"];

  return (
    <div className="files-grid">
      <section className="wide-panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">{zhCN.files.eyebrow}</p>
            <h2>{zhCN.files.title}</h2>
          </div>
          <button type="button" className="secondary-button" disabled>
            <FolderOpen size={18} weight="bold" aria-hidden />
            {zhCN.files.openFolder}
          </button>
        </div>
        <p className="muted-copy">{zhCN.files.safetyNote}</p>
      </section>

      <section className="file-kind-panel">
        <h2>{zhCN.files.byType}</h2>
        <div className="file-kind-grid">
          {groups.map((group) => (
            <div key={group}>
              <strong>{group.toUpperCase()}</strong>
              <span>{files.filter((file) => file.toLowerCase().endsWith(group)).length}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="recent-files-panel">
        <h2>{zhCN.files.recentPaths}</h2>
        {files.length > 0 ? (
          <ul className="file-list">
            {files.map((file) => (
              <li key={file}>
                <Archive size={17} weight="duotone" aria-hidden />
                <code>{file}</code>
              </li>
            ))}
          </ul>
        ) : (
          <div className="empty-state">
            <Archive size={22} weight="duotone" />
            <span>{zhCN.files.empty}</span>
          </div>
        )}
      </section>

      <section className="recent-files-panel">
        <h2>{zhCN.files.realEvidence}</h2>
        <div className="evidence-panel">
          <strong>Run: {run?.real_execution_verified ? "verified" : "unverified"}</strong>
          <small>Action: {lastAction?.real_execution_verified ? "verified" : "unverified"}</small>
          <small>active_document_after: {run?.evidence?.active_document_after ? String(run.evidence.active_document_after) : lastAction?.active_document_after || "未记录"}</small>
          <small>created_files_exist: {String(run?.evidence?.created_files_exist ?? lastAction?.created_files_exist ?? false)}</small>
        </div>
      </section>
    </div>
  );
}
