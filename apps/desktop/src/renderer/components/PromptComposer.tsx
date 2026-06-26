import { ArrowSquareOut, Brain, Check, Code, Play } from "@phosphor-icons/react";
import { useState } from "react";
import type { AIPlanResponse, GenerateScriptResponse } from "../lib/types";
import { zhCN } from "../lib/copy/zhCN";

interface PromptComposerProps {
  activeProfileId: string;
  outputDir: string;
  plan: AIPlanResponse | null;
  generated: GenerateScriptResponse | null;
  busy: boolean;
  llmVerified: boolean;
  llmBlockReason: string;
  canRunRealSolidWorks: boolean;
  solidworksBlockReason: string;
  onPlan: (prompt: string) => Promise<void>;
  onGenerate: (prompt: string) => Promise<void>;
  onApprove: () => Promise<void>;
}

const templates = zhCN.prompt.templates;

export function PromptComposer({
  activeProfileId,
  outputDir,
  plan,
  generated,
  busy,
  llmVerified,
  llmBlockReason,
  canRunRealSolidWorks,
  solidworksBlockReason,
  onPlan,
  onGenerate,
  onApprove
}: PromptComposerProps) {
  const [prompt, setPrompt] = useState<string>(zhCN.prompt.defaultPrompt);
  const generatedIsReal = Boolean(generated && !generated.demo_mode && !generated.fallback_used);
  const planDisabled = busy || prompt.trim().length === 0 || !llmVerified;
  const generateDisabled = busy || prompt.trim().length === 0 || !llmVerified;
  const approveDisabled = busy || !generatedIsReal || !canRunRealSolidWorks;

  return (
    <section className="composer-panel" aria-labelledby="prompt-composer-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">{zhCN.prompt.eyebrow}</p>
          <h2 id="prompt-composer-title">{zhCN.prompt.title}</h2>
        </div>
        <div className="profile-chip">
          <Brain size={16} weight="duotone" aria-hidden />
          {activeProfileId}
        </div>
      </div>

      <label className="input-stack">
        <span>{zhCN.prompt.requestLabel}</span>
        <textarea
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
          rows={7}
          placeholder={zhCN.prompt.placeholder}
        />
      </label>

      <div className="template-row" aria-label={zhCN.prompt.templatesLabel}>
        {templates.map((template) => (
          <button key={template} type="button" onClick={() => setPrompt(template)}>
            {template}
          </button>
        ))}
      </div>

      <div className="composer-actions">
        <button type="button" className="secondary-button" disabled={planDisabled} onClick={() => onPlan(prompt)}>
          <ArrowSquareOut size={18} weight="bold" aria-hidden />
          {zhCN.prompt.planButton}
        </button>
        <button type="button" className="primary-button" disabled={generateDisabled} onClick={() => onGenerate(prompt)}>
          <Code size={18} weight="bold" aria-hidden />
          {zhCN.prompt.generateButton}
        </button>
        <button type="button" className="approval-button" disabled={approveDisabled} onClick={onApprove}>
          <Check size={18} weight="bold" aria-hidden />
          {zhCN.prompt.approveButton}
        </button>
      </div>
      {!llmVerified ? <div className="inline-error" role="status">{llmBlockReason}</div> : null}
      {generated && !generatedIsReal ? <div className="inline-error" role="alert">{zhCN.prompt.rejectedNonReal}</div> : null}
      {generatedIsReal && !canRunRealSolidWorks ? <div className="inline-error" role="status">{solidworksBlockReason}</div> : null}

      <div className="composer-result-grid">
        <section className="result-panel">
          <h3>{zhCN.prompt.executionPlan}</h3>
          {plan ? (
            <>
              <p>{plan.plan}</p>
              <ul>
                {plan.risks.map((risk) => (
                  <li key={risk}>{risk}</li>
                ))}
              </ul>
            </>
          ) : (
            <p className="muted-copy">{zhCN.prompt.noPlan}</p>
          )}
        </section>
        <section className="result-panel script-preview">
          <h3>{zhCN.prompt.scriptPreview}</h3>
          {generated ? (
            <>
              <div className="script-meta">
                <span>{generated.demo_mode || generated.fallback_used ? zhCN.prompt.rejectedNonReal : zhCN.prompt.liveProvider}</span>
                {generated.provider_verified_at ? <span>{zhCN.prompt.providerVerified}: {new Date(generated.provider_verified_at).toLocaleString("zh-CN")}</span> : null}
                {generated.fallback_used ? <span>{generated.fallback_reason || zhCN.prompt.rejectedNonReal}</span> : null}
                <span>{outputDir || zhCN.prompt.configuredOutput}</span>
              </div>
              <pre tabIndex={0}>{generated.script}</pre>
            </>
          ) : (
            <div className="empty-state">
              <Play size={22} weight="duotone" />
              <span>{zhCN.prompt.scriptEmpty}</span>
            </div>
          )}
        </section>
      </div>
    </section>
  );
}
