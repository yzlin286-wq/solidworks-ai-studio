import { DownloadSimple, TerminalWindow } from "@phosphor-icons/react";
import { useState } from "react";
import type { RunRecord } from "../lib/types";
import { StatusBadge } from "../components/StatusBadge";
import { Timeline } from "../components/Timeline";
import { stageLabel, zhCN } from "../lib/copy/zhCN";

interface ExecutionMonitorPageProps {
  run: RunRecord | null;
}

export function ExecutionMonitorPage({ run }: ExecutionMonitorPageProps) {
  const [tab, setTab] = useState<"stdout" | "stderr">("stdout");

  return (
    <div className="monitor-grid">
      <section className="wide-panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">{zhCN.monitor.eyebrow}</p>
            <h2>{run ? `Run ${run.run_id}` : zhCN.monitor.noActiveRun}</h2>
          </div>
          {run ? <StatusBadge status={run.stage === "failed" ? "fail" : run.stage === "done" ? "pass" : "info"} label={stageLabel(run.stage)} /> : null}
        </div>
        <Timeline events={run?.events ?? []} />
      </section>

      <section className="terminal-panel">
        <div className="tab-row" role="tablist" aria-label={zhCN.monitor.outputAria}>
          <button type="button" className={tab === "stdout" ? "active" : ""} onClick={() => setTab("stdout")}>
            <TerminalWindow size={17} weight="duotone" aria-hidden />
            stdout
          </button>
          <button type="button" className={tab === "stderr" ? "active" : ""} onClick={() => setTab("stderr")}>
            <TerminalWindow size={17} weight="duotone" aria-hidden />
            stderr
          </button>
        </div>
        <pre tabIndex={0}>{tab === "stdout" ? run?.stdout || zhCN.monitor.noStdout : run?.stderr || zhCN.monitor.noStderr}</pre>
      </section>

      <section className="files-panel">
        <h2>{zhCN.monitor.generatedFiles}</h2>
        {run && run.files.length > 0 ? (
          <ul className="file-list">
            {run.files.map((file) => (
              <li key={file}>
                <DownloadSimple size={17} weight="duotone" aria-hidden />
                <code>{file}</code>
              </li>
            ))}
          </ul>
        ) : (
          <div className="empty-state">
            <DownloadSimple size={22} weight="duotone" />
            <span>{zhCN.monitor.generatedFilesEmpty}</span>
          </div>
        )}
      </section>

      <section className="files-panel">
        <h2>{zhCN.monitor.realEvidence}</h2>
        {run?.evidence && Object.keys(run.evidence).length > 0 ? (
          <div className="evidence-panel">
            <strong>{run.real_execution_verified ? "real_execution_verified=true" : "real_execution_verified=false"}</strong>
            <small>active_document_before: {String(run.evidence.active_document_before ?? "未记录")}</small>
            <small>active_document_after: {String(run.evidence.active_document_after ?? "未记录")}</small>
            <small>created_files_exist: {String(run.evidence.created_files_exist ?? false)}</small>
          </div>
        ) : (
          <div className="empty-state">
            <DownloadSimple size={22} weight="duotone" />
            <span>{zhCN.monitor.noEvidence}</span>
          </div>
        )}
      </section>
    </div>
  );
}
