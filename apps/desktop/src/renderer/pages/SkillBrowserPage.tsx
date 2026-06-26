import { MagnifyingGlass, Stack } from "@phosphor-icons/react";
import { useMemo, useState } from "react";
import type { Capability, SkillIndexResponse } from "../lib/types";
import { StatusBadge } from "../components/StatusBadge";
import { addinRequirementLabel, executionKindLabel, realValidationStatusLabel, zhCN } from "../lib/copy/zhCN";

interface SkillBrowserPageProps {
  skills: SkillIndexResponse | null;
  capabilities: Capability[];
  busy: boolean;
  onSync: () => Promise<void>;
}

export function SkillBrowserPage({ skills, capabilities = [], busy, onSync }: SkillBrowserPageProps) {
  const [query, setQuery] = useState("");
  const documents = useMemo(() => {
    if (!skills) {
      return [];
    }
    const needle = query.toLowerCase();
    return skills.documents.filter((doc) => `${doc.title} ${doc.path} ${doc.excerpt}`.toLowerCase().includes(needle));
  }, [query, skills]);
  const functions = useMemo(() => {
    if (!skills) {
      return [];
    }
    const needle = query.toLowerCase();
    return skills.functions.filter((fn) => `${fn.module} ${fn.signature} ${fn.doc}`.toLowerCase().includes(needle)).slice(0, 80);
  }, [query, skills]);
  const filteredCapabilities = useMemo(() => {
    const needle = query.toLowerCase();
    return capabilities.filter((capability) =>
      `${capability.id} ${capability.title} ${capability.source_path} ${capability.real_sw2025_status} ${capability.skip_reason}`
        .toLowerCase()
        .includes(needle)
    );
  }, [capabilities, query]);

  return (
    <div className="skill-browser-grid">
      <section className="wide-panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">{zhCN.skills.eyebrow}</p>
            <h2>{zhCN.skills.title}</h2>
          </div>
          <button type="button" className="secondary-button" disabled={busy} onClick={onSync}>
            <Stack size={18} weight="bold" aria-hidden />
            {zhCN.skills.sync}
          </button>
        </div>
        <div className="search-field">
          <MagnifyingGlass size={18} aria-hidden />
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={zhCN.skills.searchPlaceholder} />
        </div>
        <div className="skill-summary">
          <StatusBadge status={skills?.solidworks_available ? "pass" : "fail"} label={zhCN.skills.solidworksSkill} />
          <StatusBadge status={skills?.taste_available ? "pass" : "fail"} label={zhCN.skills.tasteSkill} />
          <span>{skills ? `${skills.documents.length} ${zhCN.skills.documentsIndexed}` : "索引加载中"}</span>
          <span>{skills ? `${skills.functions.length} ${zhCN.skills.functionsIndexed}` : "函数加载中"}</span>
          <span>{skills ? `${skills.mcp_tools.length} ${zhCN.skills.mcpToolsIndexed}` : "MCP 加载中"}</span>
          <span>{`${capabilities.length} ${zhCN.skills.capabilitiesIndexed}`}</span>
        </div>
        <p className="context-summary">{skills?.context_summary ?? zhCN.skills.loadingContext}</p>
      </section>

      <section className="capability-list-panel">
        <h2>{zhCN.skills.capabilityMatrix}</h2>
        <div className="scroll-list">
          {filteredCapabilities.map((capability) => (
            <article key={capability.id} className="indexed-row capability-row">
              <div>
                <strong>{capability.title}</strong>
                <span>{realValidationStatusLabel(capability.real_sw2025_status)}</span>
              </div>
              <p>
                {capability.callable ? zhCN.skills.callable : zhCN.skills.contextOnly} · {executionKindLabel(capability.execution_kind)} · {addinRequirementLabel(capability.requires_addin)}
              </p>
              {capability.skip_reason ? <p>{capability.skip_reason}</p> : null}
              <code>{capability.id}</code>
              <code>{capability.source_path}</code>
            </article>
          ))}
        </div>
      </section>

      <section className="document-list-panel">
        <h2>{zhCN.skills.documents}</h2>
        <div className="scroll-list">
          {documents.map((doc) => (
            <article key={doc.path} className="indexed-row">
              <div>
                <strong>{doc.title}</strong>
                <span>{doc.kind}</span>
              </div>
              <p>{doc.excerpt}</p>
              <code>{doc.path}</code>
            </article>
          ))}
        </div>
      </section>

      <section className="function-list-panel">
        <h2>{zhCN.skills.functions}</h2>
        <div className="scroll-list">
          {functions.map((fn) => (
            <article key={`${fn.module}.${fn.signature}`} className="indexed-row">
              <div>
                <strong>{fn.module}</strong>
                <span>{fn.name}</span>
              </div>
              <code>{fn.signature}</code>
              {fn.doc ? <p>{fn.doc}</p> : null}
            </article>
          ))}
          {skills?.mcp_tools.map((tool) => (
            <article key={tool} className="indexed-row mcp-tool-row">
              <div>
                <strong>{tool}</strong>
                <span>MCP</span>
              </div>
              <p>{zhCN.skills.mcpDescription}</p>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
