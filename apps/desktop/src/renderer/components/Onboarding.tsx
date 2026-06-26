import { ArrowRight, Brain, Checks, FolderOpen, PlugsConnected } from "@phosphor-icons/react";
import type { ReactNode } from "react";
import type { ConfigResponse, HealthResponse, PreflightResponse, RealTestRunResponse, SkillIndexResponse } from "../lib/types";
import { modeLabel, preflightBadgeStatus, preflightStatusLabel, statusLevelLabel, zhCN } from "../lib/copy/zhCN";
import { StatusBadge } from "./StatusBadge";

interface OnboardingProps {
  health: HealthResponse | null;
  config: ConfigResponse | null;
  preflight: PreflightResponse | null;
  skills: SkillIndexResponse | null;
  realReport: RealTestRunResponse | null;
  onEnter: () => void;
  onRefresh: () => void;
}

export function Onboarding({ health, config, preflight, skills, realReport, onEnter, onRefresh }: OnboardingProps) {
  return (
    <div className="onboarding-screen">
      <div className="onboarding-panel">
        <div className="onboarding-copy">
          <p className="eyebrow">{zhCN.onboarding.eyebrow}</p>
          <h1>{zhCN.onboarding.headline}</h1>
          <p>{zhCN.onboarding.intro}</p>
          <div className="onboarding-actions">
            <button type="button" className="primary-button" onClick={onEnter}>
              {zhCN.onboarding.enterWorkspace}
              <ArrowRight size={18} weight="bold" aria-hidden />
            </button>
            <button type="button" className="secondary-button" onClick={onRefresh}>
              {zhCN.onboarding.refreshChecks}
            </button>
          </div>
        </div>
        <div className="onboarding-grid" aria-label={zhCN.onboarding.readinessLabel}>
          <ReadinessTile
            icon={<PlugsConnected size={24} weight="duotone" />}
            title={zhCN.onboarding.tiles.api}
            status={health?.ok ? "pass" : "warn"}
            detail={health?.ok ? `Backend ${health.version}` : zhCN.onboarding.details.backendWaiting}
          />
          <ReadinessTile
            icon={<Brain size={24} weight="duotone" />}
            title={zhCN.onboarding.tiles.llm}
            status={config?.config.profiles.some((profile) => profile.api_key && profile.api_key !== "********") ? "pass" : "info"}
            detail={config ? `${zhCN.onboarding.details.activeProfile}: ${config.config.active_profile_id}` : zhCN.onboarding.details.profilesLoading}
          />
          <ReadinessTile
            icon={<Checks size={24} weight="duotone" />}
            title={zhCN.onboarding.tiles.preflight}
            status={preflightBadgeStatus(preflight)}
            detail={preflight ? `${preflightStatusLabel(preflight)} · ${modeLabel(preflight.mode)} · SW ${preflight.solidworks_version || zhCN.onboarding.details.swUnknown}` : zhCN.onboarding.details.preflightLoading}
          />
          <ReadinessTile
            icon={<FolderOpen size={24} weight="duotone" />}
            title={zhCN.onboarding.tiles.skills}
            status={skills?.solidworks_available && skills.taste_available ? "pass" : "fail"}
            detail={skills ? `${skills.documents.length} 份文档，${skills.functions.length} 个函数` : zhCN.onboarding.details.indexLoading}
          />
          <ReadinessTile
            icon={<Checks size={24} weight="duotone" />}
            title={zhCN.onboarding.tiles.realValidation}
            status={realReport?.ok ? "pass" : "warn"}
            detail={realReport ? `${realReport.core_passed} 项核心通过，${realReport.core_failed} 项核心失败` : zhCN.onboarding.details.noRealValidation}
          />
        </div>
      </div>
    </div>
  );
}

interface ReadinessTileProps {
  icon: ReactNode;
  title: string;
  status: "pass" | "warn" | "fail" | "info";
  detail: string;
}

function ReadinessTile({ icon, title, status, detail }: ReadinessTileProps) {
  return (
    <section className="readiness-tile">
      <div className="tile-icon">{icon}</div>
      <div>
        <h2>{title}</h2>
        <StatusBadge status={status} label={statusLevelLabel(status)} />
        <p>{detail}</p>
      </div>
    </section>
  );
}
