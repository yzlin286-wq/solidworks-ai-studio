import { CheckCircle, Info, Warning, WarningCircle } from "@phosphor-icons/react";
import type { StatusLevel } from "../lib/types";

interface StatusBadgeProps {
  status: StatusLevel;
  label: string;
}

const iconMap = {
  pass: CheckCircle,
  warn: Warning,
  fail: WarningCircle,
  info: Info
};

export function StatusBadge({ status, label }: StatusBadgeProps) {
  const Icon = iconMap[status];
  return (
    <span className={`status-badge status-${status}`}>
      <Icon size={15} weight="duotone" aria-hidden />
      {label}
    </span>
  );
}
