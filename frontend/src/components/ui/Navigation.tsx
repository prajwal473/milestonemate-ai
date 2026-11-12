import { CheckCircle2, Circle, Clock } from "lucide-react";
import { Link } from "react-router-dom";
import { formatDate, formatMoney } from "../../lib/format";
import { StatusBadge } from "./Badge";

export interface TabItem {
  id: string;
  label: string;
  to: string;
  count?: number;
}

export function Tabs({ items, activeId }: { items: TabItem[]; activeId: string }) {
  return (
    <nav aria-label="Project sections" className="border-b border-ink-300/70">
      <div className="-mb-px flex gap-1 overflow-x-auto">
        {items.map((item) => {
          const active = item.id === activeId;
          return (
            <Link
              key={item.id}
              to={item.to}
              aria-current={active ? "page" : undefined}
              className={`inline-flex min-h-[44px] shrink-0 items-center gap-2 border-b-2 px-3.5 py-2.5 text-sm font-medium transition ${
                active
                  ? "border-brand-600 text-brand-600"
                  : "border-transparent text-ink-600 hover:border-ink-300 hover:text-ink-900"
              }`}
            >
              <span>{item.label}</span>
              {typeof item.count === "number" && (
                <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-semibold text-ink-700">
                  {item.count}
                </span>
              )}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}

export interface StepperMilestoneItem {
  id: number;
  title: string;
  amount: string;
  dueDate: string;
  status: string;
  to: string;
}

export function MilestoneStepper({ items }: { items: StepperMilestoneItem[] }) {
  return (
    <ol className="grid gap-3 md:grid-cols-3">
      {items.map((item, idx) => {
        const normalized = item.status.toLowerCase();
        const isDone = normalized === "paid" || normalized === "approved";
        const isCurrent = normalized === "submitted" || normalized === "revision_requested";
        const Icon = isDone ? CheckCircle2 : isCurrent ? Clock : Circle;
        const iconClass = isDone
          ? "text-success-600"
          : isCurrent
            ? "text-brand-600"
            : "text-ink-500";

        return (
          <li key={item.id}>
            <Link
              to={item.to}
              className="flex h-full flex-col justify-between gap-3 rounded-xl border border-ink-300/70 bg-surface p-4 shadow-sm transition hover:border-brand-600/60 hover:bg-brand-50/20"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2">
                  <Icon className={`h-5 w-5 shrink-0 ${iconClass}`} aria-hidden="true" />
                  <span className="text-xs font-semibold uppercase tracking-wide text-ink-500">
                    Milestone {idx + 1}
                  </span>
                </div>
                <StatusBadge status={item.status} context="milestone" />
              </div>
              <div>
                <p className="font-semibold text-ink-900">{item.title}</p>
                <div className="mt-2 flex items-center justify-between text-xs text-ink-600">
                  <span className="font-semibold tabular-nums text-ink-900">
                    {formatMoney(item.amount)}
                  </span>
                  <span>Due {formatDate(item.dueDate)}</span>
                </div>
              </div>
            </Link>
          </li>
        );
      })}
    </ol>
  );
}

