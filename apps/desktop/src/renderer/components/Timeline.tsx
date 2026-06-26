import { Circle, CheckCircle, Clock, XCircle } from "@phosphor-icons/react";
import type { RunEvent, RunStage } from "../lib/types";
import { stageLabel, zhCN } from "../lib/copy/zhCN";

interface TimelineProps {
  events: RunEvent[];
}

const stageIcon: Record<RunStage, typeof Circle> = {
  queued: Clock,
  planning: Circle,
  generated: Circle,
  waiting_approval: Circle,
  running: Clock,
  reviewing: Circle,
  done: CheckCircle,
  failed: XCircle
};

export function Timeline({ events }: TimelineProps) {
  if (events.length === 0) {
    return (
      <div className="empty-state">
        <Clock size={22} weight="duotone" />
        <span>{zhCN.timeline.empty}</span>
      </div>
    );
  }

  return (
    <ol className="timeline-list" aria-label={zhCN.timeline.ariaLabel}>
      {events.map((event, index) => {
        const Icon = stageIcon[event.stage];
        return (
          <li key={`${event.stage}-${event.time}-${index}`} className="timeline-item">
            <Icon size={18} weight="duotone" aria-hidden />
            <div>
              <strong>{stageLabel(event.stage)}</strong>
              <p>{event.message}</p>
              <time>{new Date(event.time).toLocaleTimeString()}</time>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
