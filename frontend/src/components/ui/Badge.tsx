import type { ReactNode } from "react";
import { getStatusStyle, type BadgeTone } from "../../lib/statusStyles";

const toneClasses: Record<BadgeTone, string> = {
  gray: "bg-slate-100 text-ink-700 border-slate-200",
  brand: "bg-brand-50 text-brand-700 border-brand-100",
  success: "bg-success-50 text-success-700 border-emerald-200",
  warning: "bg-warning-50 text-warning-700 border-amber-200",
  danger: "bg-danger-50 text-danger-700 border-red-200",
  ai: "bg-ai-50 text-ai-700 border-violet-200",
};

const dotClasses: Record<BadgeTone, string> = {
  gray: "bg-ink-500",
  brand: "bg-brand-600",
  success: "bg-success-600",
  warning: "bg-warning-600",
  danger: "bg-danger-600",
  ai: "bg-ai-600",
};

export interface BadgeProps {
  tone?: BadgeTone;
  children: ReactNode;
  dot?: boolean;
  className?: string;
}

export function Badge({ tone = "gray", children, dot = false, className = "" }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium ${toneClasses[tone]} ${className}`}
    >
      {dot && <span className={`h-1.5 w-1.5 rounded-full ${dotClasses[tone]}`} aria-hidden="true" />}
      {children}
    </span>
  );
}

export interface StatusBadgeProps {
  status: string | null | undefined;
  context?: "agreement" | "milestone";
  className?: string;
}

export function StatusBadge({ status, context, className = "" }: StatusBadgeProps) {
  const { label, tone } = getStatusStyle(status, context);
  return (
    <Badge tone={tone} dot className={className}>
      {label}
    </Badge>
  );
}

