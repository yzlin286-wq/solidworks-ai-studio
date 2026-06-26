import { ClipboardText, Copy, ImageSquare, Sparkle } from "@phosphor-icons/react";
import type { RunRecord, SolidWorksActionResponse } from "../lib/types";
import { zhCN } from "../lib/copy/zhCN";

interface ReviewCenterPageProps {
  run: RunRecord | null;
  lastAction: SolidWorksActionResponse | null;
  onCopyReviewPrompt: () => void;
}

export function ReviewCenterPage({ run, lastAction, onCopyReviewPrompt }: ReviewCenterPageProps) {
  const realReady = Boolean(run?.real_execution_verified || lastAction?.real_execution_verified);
  const reviewFiles = [...(run?.files ?? []), ...(lastAction?.files ?? [])].filter((file) =>
    [".json", ".bmp", ".png", ".jpg", ".jpeg"].some((suffix) => file.toLowerCase().endsWith(suffix))
  );

  return (
    <div className="review-grid">
      <section className="wide-panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">{zhCN.review.eyebrow}</p>
            <h2>{zhCN.review.title}</h2>
          </div>
          <button type="button" className="secondary-button" onClick={onCopyReviewPrompt}>
            <Copy size={18} weight="bold" aria-hidden />
            {zhCN.review.copyFixPrompt}
          </button>
        </div>
        <div className="checklist-grid">
          {zhCN.review.items.map((item) => (
            <div key={item} className="checklist-item">
              <ClipboardText size={18} weight="duotone" aria-hidden />
              <span>{item}</span>
              <strong>{realReady ? zhCN.review.ready : zhCN.review.waiting}</strong>
            </div>
          ))}
        </div>
      </section>

      <section className="review-report-panel">
        <h2>review_report.json</h2>
        <pre tabIndex={0}>
          {JSON.stringify(
            {
              activeRun: run?.run_id ?? null,
              lastAction: lastAction?.action ?? null,
              status: run?.stage ?? "not_started",
              real_execution_verified: realReady,
              files: reviewFiles
            },
            null,
            2
          )}
        </pre>
      </section>

      <section className="preview-panel">
        <h2>{zhCN.review.previewImages}</h2>
        {reviewFiles.filter((file) => !file.toLowerCase().endsWith(".json")).length > 0 ? (
          <div className="preview-grid">
            {reviewFiles
              .filter((file) => !file.toLowerCase().endsWith(".json"))
              .map((file) => (
                <div key={file} className="preview-slot">
                  <ImageSquare size={22} weight="duotone" aria-hidden />
                  <code>{file}</code>
                </div>
              ))}
          </div>
        ) : (
          <div className="empty-state">
            <Sparkle size={22} weight="duotone" />
            <span>{zhCN.review.previewEmpty}</span>
          </div>
        )}
      </section>
    </div>
  );
}
