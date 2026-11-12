import { useState, type ReactNode } from "react";
import { AlertTriangle, Check, Copy, Info, RefreshCw, Sparkles } from "lucide-react";
import { formatDate, formatMoney, initialsFromName } from "../../lib/format";
import { Button } from "./Button";

export function Skeleton({ className = "h-4 w-full" }: { className?: string }) {
  return <div className={`animate-pulse rounded-lg bg-slate-200/80 ${className}`} aria-hidden="true" />;
}

export function Banner({
  tone = "info",
  children,
  action,
}: {
  tone?: "info" | "warning" | "ai";
  children: ReactNode;
  action?: ReactNode;
}) {
  const classes =
    tone === "warning"
      ? "border-amber-200 bg-warning-50 text-warning-700"
      : tone === "ai"
        ? "border-violet-200 bg-ai-50 text-ai-700"
        : "border-brand-100 bg-brand-50 text-brand-700";

  return (
    <div
      role="status"
      className={`flex flex-wrap items-center justify-between gap-2 border-b px-4 py-2 text-xs font-medium ${classes}`}
    >
      <div className="flex items-center gap-2">
        {tone === "warning" ? (
          <AlertTriangle className="h-4 w-4 shrink-0" aria-hidden="true" />
        ) : tone === "ai" ? (
          <Sparkles className="h-4 w-4 shrink-0" aria-hidden="true" />
        ) : (
          <Info className="h-4 w-4 shrink-0" aria-hidden="true" />
        )}
        <span>{children}</span>
      </div>
      {action}
    </div>
  );
}

export function EmptyState({
  icon,
  title,
  description,
  action,
}: {
  icon?: ReactNode;
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-ink-300 bg-surface px-6 py-10 text-center">
      {icon && <div className="mb-3 rounded-full bg-brand-50 p-3 text-brand-600">{icon}</div>}
      <h3 className="text-base font-semibold text-ink-900">{title}</h3>
      <p className="mt-1 max-w-md text-sm text-ink-600">{description}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function ErrorState({
  message,
  requestId,
  onRetry,
}: {
  message: string;
  requestId?: string;
  onRetry?: () => void;
}) {
  return (
    <div
      role="alert"
      className="flex flex-col items-start justify-between gap-4 rounded-xl border border-red-200 bg-danger-50 p-5 sm:flex-row sm:items-center"
    >
      <div className="space-y-1">
        <p className="text-sm font-semibold text-danger-700">Something went wrong</p>
        <p className="text-sm text-ink-900">{message}</p>
        {requestId && (
          <p className="font-mono text-xs text-ink-600">Request ID: {requestId}</p>
        )}
      </div>
      {onRetry && (
        <Button
          variant="secondary"
          size="sm"
          onClick={onRetry}
          icon={<RefreshCw className="h-3.5 w-3.5" />}
        >
          Retry
        </Button>
      )}
    </div>
  );
}

export function AiChip({ label = "AI-generated" }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-violet-200 bg-ai-50 px-2.5 py-0.5 text-xs font-medium text-ai-700">
      <Sparkles className="h-3 w-3" aria-hidden="true" />
      {label}
    </span>
  );
}

export function Copyable({
  value,
  label,
  truncate = false,
}: {
  value: string;
  label?: string;
  truncate?: boolean;
}) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      // ignore clipboard restrictions
    }
  }

  return (
    <div className="inline-flex max-w-full items-center gap-2 rounded-lg border border-ink-300/80 bg-canvas px-2.5 py-1.5">
      {label && <span className="text-xs font-medium text-ink-600">{label}:</span>}
      <code className={`font-mono text-xs text-ink-900 ${truncate ? "max-w-[180px] truncate" : "break-all"}`}>
        {value}
      </code>
      <button
        type="button"
        onClick={() => void handleCopy()}
        aria-label={copied ? "Copied" : `Copy ${label ?? "value"}`}
        className="rounded p-1 text-ink-500 hover:bg-surface hover:text-ink-900"
      >
        {copied ? <Check className="h-3.5 w-3.5 text-success-600" /> : <Copy className="h-3.5 w-3.5" />}
      </button>
    </div>
  );
}

export function MoneyText({
  value,
  currency = "USD",
  className = "",
}: {
  value: string | number | null | undefined;
  currency?: string;
  className?: string;
}) {
  return <span className={`font-semibold tabular-nums ${className}`}>{formatMoney(value, currency)}</span>;
}

export function DateText({
  value,
  className = "",
}: {
  value: string | null | undefined;
  className?: string;
}) {
  return (
    <time dateTime={value ?? undefined} className={className}>
      {formatDate(value)}
    </time>
  );
}

export function Avatar({ name, size = "md" }: { name: string; size?: "sm" | "md" }) {
  const dims = size === "sm" ? "h-8 w-8 text-xs" : "h-10 w-10 text-sm";
  return (
    <span
      aria-hidden="true"
      className={`inline-flex items-center justify-center rounded-full bg-brand-100 font-semibold text-brand-700 ${dims}`}
    >
      {initialsFromName(name)}
    </span>
  );
}

