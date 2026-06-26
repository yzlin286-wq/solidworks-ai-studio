import { FloppyDisk, Key, Moon, PlugsConnected, Sun, TestTube } from "@phosphor-icons/react";
import { useEffect, useState } from "react";
import { api } from "../lib/api";
import type { AppConfig, ConfigResponse, LLMProfile, MCPConfigSnippetsResponse, MCPStatusResponse, TestConnectionResponse } from "../lib/types";
import { StatusBadge } from "../components/StatusBadge";
import { zhCN } from "../lib/copy/zhCN";

interface SettingsPageProps {
  configResponse: ConfigResponse | null;
  mcp: MCPStatusResponse | null;
  busy: boolean;
  onSave: (config: AppConfig) => Promise<void>;
  onConnectionTest: (connection: TestConnectionResponse) => void;
  onMcpStart: () => Promise<void>;
  onMcpStop: () => Promise<void>;
}

export function SettingsPage({ configResponse, mcp, busy, onSave, onConnectionTest, onMcpStart, onMcpStop }: SettingsPageProps) {
  const [draft, setDraft] = useState<AppConfig | null>(configResponse?.config ?? null);
  const [connection, setConnection] = useState<TestConnectionResponse | null>(null);
  const [testingConnection, setTestingConnection] = useState(false);
  const [snippets, setSnippets] = useState<MCPConfigSnippetsResponse | null>(null);

  useEffect(() => {
    setDraft(configResponse?.config ?? null);
  }, [configResponse]);

  useEffect(() => {
    api.mcpSnippets().then(setSnippets).catch(() => setSnippets(null));
  }, []);

  if (!draft) {
    return <div className="empty-state">{zhCN.settings.loading}</div>;
  }

  const activeProfile = draft.profiles.find((profile) => profile.id === draft.active_profile_id) ?? draft.profiles[0];

  function updateActiveProfile(next: Partial<LLMProfile>): void {
    setDraft((current) => {
      if (!current) {
        return current;
      }
      return {
        ...current,
        profiles: current.profiles.map((profile) =>
          profile.id === current.active_profile_id ? { ...profile, ...next } : profile
        )
      };
    });
  }

  return (
    <div className="settings-grid">
      <section className="wide-panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">{zhCN.settings.eyebrow}</p>
            <h2>{zhCN.settings.title}</h2>
          </div>
          <button type="button" className="primary-button" disabled={busy} onClick={() => onSave({ ...draft, mock_mode: false })}>
            <FloppyDisk size={18} weight="bold" aria-hidden />
            {zhCN.settings.save}
          </button>
        </div>
        <p className="muted-copy">{configResponse?.note}</p>
        <code className="path-strip">{configResponse?.config_path}</code>
      </section>

      <section className="settings-panel">
        <h2>{zhCN.settings.llmProfile}</h2>
        <label className="input-stack">
          <span>{zhCN.settings.profile}</span>
          <select value={draft.active_profile_id} onChange={(event) => setDraft({ ...draft, active_profile_id: event.target.value })}>
            {draft.profiles.map((profile) => (
              <option key={profile.id} value={profile.id}>
                {profile.name}
              </option>
            ))}
          </select>
        </label>
        <label className="input-stack">
          <span>{zhCN.settings.apiBaseUrl}</span>
          <input
            value={activeProfile.api_base_url}
            onChange={(event) => updateActiveProfile({ api_base_url: event.target.value })}
            placeholder={zhCN.settings.recommendedBaseUrl}
          />
        </label>
        <label className="input-stack">
          <span>{zhCN.settings.apiKey}</span>
          <input
            type="password"
            value={activeProfile.api_key === "********" ? "" : activeProfile.api_key}
            onChange={(event) => updateActiveProfile({ api_key: event.target.value })}
            placeholder={zhCN.settings.apiKeyPlaceholder}
          />
        </label>
        <div className="settings-two-col">
          <label className="input-stack">
            <span>{zhCN.settings.model}</span>
            <input
              list="swai-model-options"
              value={activeProfile.model}
              onChange={(event) => updateActiveProfile({ model: event.target.value })}
              placeholder={zhCN.settings.modelPlaceholder}
            />
            <datalist id="swai-model-options">
              {zhCN.settings.modelOptions.map((model) => (
                <option key={model} value={model} />
              ))}
            </datalist>
          </label>
          <label className="input-stack">
            <span>{zhCN.settings.timeout}</span>
            <input
              type="number"
              value={activeProfile.timeout_seconds}
              onChange={(event) => updateActiveProfile({ timeout_seconds: Number(event.target.value) })}
            />
          </label>
          <label className="input-stack">
            <span>{zhCN.settings.temperature}</span>
            <input
              type="number"
              step="0.1"
              min="0"
              max="2"
              value={activeProfile.temperature}
              onChange={(event) => updateActiveProfile({ temperature: Number(event.target.value) })}
            />
          </label>
          <label className="input-stack">
            <span>{zhCN.settings.maxTokens}</span>
            <input
              type="number"
              value={activeProfile.max_tokens}
              onChange={(event) => updateActiveProfile({ max_tokens: Number(event.target.value) })}
            />
          </label>
        </div>
        <button
          type="button"
          className="secondary-button"
          disabled={busy || testingConnection}
          onClick={async () => {
            setTestingConnection(true);
            try {
              const result = await api.testConnection(activeProfile);
              setConnection(result);
              onConnectionTest(result);
            } catch (caught) {
              const result = {
                ok: false,
                provider: activeProfile.name,
                message: caught instanceof Error ? caught.message : String(caught),
                latency_ms: null,
                models: [],
                models_verified: false,
                chat_verified: false
              };
              setConnection(result);
              onConnectionTest(result);
            } finally {
              setTestingConnection(false);
            }
          }}
        >
          <TestTube size={18} weight="bold" aria-hidden />
          {testingConnection ? zhCN.settings.testingConnection : zhCN.settings.testConnection}
        </button>
        {connection ? (
          <div className="connection-result">
            <StatusBadge status={connection.ok ? "pass" : "fail"} label={connection.message} />
            <p>
              chat: {connection.chat_verified ? "已验证" : "未验证"} · models: {connection.models_verified ? "已验证" : "未验证"}
              {connection.latency_ms ? ` · ${connection.latency_ms} ms` : ""}
            </p>
            {connection.models.length > 0 ? <code>{connection.models.join(" / ")}</code> : null}
          </div>
        ) : null}
      </section>

      <section className="settings-panel">
        <h2>{zhCN.settings.pathsSafety}</h2>
        <label className="input-stack">
          <span>{zhCN.settings.solidworksSkillPath}</span>
          <input value={draft.solidworks_skill_path} onChange={(event) => setDraft({ ...draft, solidworks_skill_path: event.target.value })} />
        </label>
        <label className="input-stack">
          <span>{zhCN.settings.tasteSkillPath}</span>
          <input value={draft.taste_skill_path} onChange={(event) => setDraft({ ...draft, taste_skill_path: event.target.value })} />
        </label>
        <label className="input-stack">
          <span>{zhCN.settings.outputDirectory}</span>
          <input value={draft.output_dir} onChange={(event) => setDraft({ ...draft, output_dir: event.target.value })} />
        </label>
        <label className="input-stack">
          <span>{zhCN.settings.validationOutputDirectory}</span>
          <input value={draft.validation_output_dir} onChange={(event) => setDraft({ ...draft, validation_output_dir: event.target.value })} />
        </label>
        <label className="input-stack">
          <span>{zhCN.settings.partTemplatePath}</span>
          <input value={draft.part_template_path} onChange={(event) => setDraft({ ...draft, part_template_path: event.target.value })} />
        </label>
        <label className="input-stack">
          <span>{zhCN.settings.assemblyTemplatePath}</span>
          <input value={draft.assembly_template_path} onChange={(event) => setDraft({ ...draft, assembly_template_path: event.target.value })} />
        </label>
        <label className="input-stack">
          <span>{zhCN.settings.drawingTemplatePath}</span>
          <input value={draft.drawing_template_path} onChange={(event) => setDraft({ ...draft, drawing_template_path: event.target.value })} />
        </label>
        <label className="toggle-line">
          <input type="checkbox" checked={draft.require_approval} onChange={(event) => setDraft({ ...draft, require_approval: event.target.checked })} />
          {zhCN.settings.requireApproval}
        </label>
        <div className="theme-buttons" role="group" aria-label={zhCN.settings.theme}>
          <button type="button" className={draft.theme === "dark" ? "active" : ""} onClick={() => setDraft({ ...draft, theme: "dark" })}>
            <Moon size={17} weight="duotone" aria-hidden />
            {zhCN.settings.dark}
          </button>
          <button type="button" className={draft.theme === "light" ? "active" : ""} onClick={() => setDraft({ ...draft, theme: "light" })}>
            <Sun size={17} weight="duotone" aria-hidden />
            {zhCN.settings.light}
          </button>
        </div>
      </section>

      <section className="settings-panel mcp-settings-panel">
        <div className="panel-heading compact">
          <div>
            <h2>{zhCN.settings.mcpConfig}</h2>
            <StatusBadge status={mcp?.running ? "pass" : "info"} label={mcp?.running ? zhCN.settings.running : zhCN.settings.stopped} />
          </div>
          <div className="button-pair">
            <button type="button" className="secondary-button" onClick={onMcpStart} disabled={busy}>
              <PlugsConnected size={18} weight="bold" aria-hidden />
              {zhCN.settings.start}
            </button>
            <button type="button" className="secondary-button" onClick={onMcpStop} disabled={busy}>
              <Key size={18} weight="bold" aria-hidden />
              {zhCN.settings.stop}
            </button>
          </div>
        </div>
        <div className="snippet-list">
          {snippets
            ? Object.entries(snippets.snippets).map(([name, snippet]) => (
                <article key={name}>
                  <strong>{name}</strong>
                  <pre tabIndex={0}>{snippet}</pre>
                </article>
              ))
            : zhCN.settings.snippetsLoading}
        </div>
      </section>
    </div>
  );
}
