import { useMemo } from "react";
import { Link } from "react-router-dom";
import { useQueries, useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  CalendarClock,
  CheckCircle2,
  CreditCard,
  FolderKanban,
  Plus,
} from "lucide-react";
import { api } from "../../api/endpoints";
import { getPaymentApi } from "../../api/paymentsAdapter";
import type { Milestone, Project } from "../../api/types";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
  MoneyText,
  Skeleton,
  StatusBadge,
} from "../../components/ui";
import { formatDate, formatMoney } from "../../lib/format";
import { useAuth } from "../auth/useAuth";

interface ActionItem {
  projectId: number;
  projectTitle: string;
  label: string;
  to: string;
  cta: string;
}

export function DashboardPage() {
  const { user } = useAuth();
  const paymentApi = getPaymentApi();

  const {
    data: projects = [],
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ["projects"],
    queryFn: api.listProjects,
  });

  const milestoneQueries = useQueries({
    queries: projects.map((project) => ({
      queryKey: ["milestones", project.id],
      queryFn: () => api.listMilestones(project.id),
      staleTime: 15_000,
    })),
  });

  const paymentQueries = useQueries({
    queries: projects.map((project) => ({
      queryKey: ["project-payments", project.id],
      queryFn: () => paymentApi.getProjectPayments(String(project.id)),
      staleTime: 15_000,
    })),
  });

  const {
    activeCount,
    dueSoonCount,
    paidTotal,
    needsAction,
    upcomingMilestones,
    recentPayments,
    projectMeta,
  } = useMemo(() => {
    const meta = new Map<
      number,
      { milestones: Milestone[]; paid: string; paidCount: number }
    >();
    const actions: ActionItem[] = [];
    const upcoming: Array<{
      projectId: number;
      projectTitle: string;
      milestone: Milestone;
      overdue: boolean;
    }> = [];
    const paymentsList: Array<{
      id: number;
      projectId: number;
      projectTitle: string;
      milestoneTitle: string;
      amount: string;
      status: string;
      createdAt: string;
    }> = [];

    let totalPaid = 0;
    let due7d = 0;
    const now = Date.now();
    const in7d = now + 7 * 24 * 60 * 60 * 1000;

    projects.forEach((project: Project, index: number) => {
      const milestones = milestoneQueries[index]?.data ?? [];
      const ledger = paymentQueries[index]?.data;
      const paidAmount = ledger ? Number.parseFloat(ledger.totals.paid) : 0;
      totalPaid += Number.isFinite(paidAmount) ? paidAmount : 0;

      const paidCount = milestones.filter((m) => m.status.toLowerCase() === "paid").length;
      meta.set(project.id, {
        milestones,
        paid: ledger?.totals.paid ?? "0.00",
        paidCount,
      });

      if (project.status.toLowerCase() === "draft") {
        actions.push({
          projectId: project.id,
          projectTitle: project.title,
          label:
            user?.role === "client"
              ? "Draft & approve project agreement"
              : "Review & approve project agreement",
          to: `/projects/${project.id}/agreement`,
          cta: "Open agreement",
        });
      }

      milestones.forEach((m) => {
        const st = m.status.toLowerCase();
        const dueMs = new Date(m.due_date).getTime();
        if (st !== "paid") {
          const overdue = Number.isFinite(dueMs) && dueMs < now;
          if (Number.isFinite(dueMs) && dueMs <= in7d) due7d += 1;
          upcoming.push({ projectId: project.id, projectTitle: project.title, milestone: m, overdue });
        }

        if (user?.role === "freelancer" && (st === "pending" || st === "revision_requested")) {
          actions.push({
            projectId: project.id,
            projectTitle: project.title,
            label:
              st === "revision_requested"
                ? `Resubmit "${m.title}"`
                : `Submit deliverable for "${m.title}"`,
            to: `/projects/${project.id}/milestones/${m.id}`,
            cta: "Submit work",
          });
        }

        if (user?.role === "client" && st === "submitted") {
          actions.push({
            projectId: project.id,
            projectTitle: project.title,
            label: `Review submission for "${m.title}"`,
            to: `/projects/${project.id}/milestones/${m.id}`,
            cta: "Evaluate",
          });
        }

        if (user?.role === "client" && st === "approved") {
          actions.push({
            projectId: project.id,
            projectTitle: project.title,
            label: `Pay accepted milestone "${m.title}" (${formatMoney(m.amount)})`,
            to: `/projects/${project.id}/milestones/${m.id}`,
            cta: `Pay ${formatMoney(m.amount)}`,
          });
        }
      });

      (ledger?.items ?? []).forEach((p) => {
        paymentsList.push({
          id: p.id,
          projectId: project.id,
          projectTitle: project.title,
          milestoneTitle: p.milestone_title ?? `Milestone #${p.milestone_id}`,
          amount: p.amount,
          status: p.status,
          createdAt: p.created_at,
        });
      });
    });

    upcoming.sort(
      (a, b) =>
        new Date(a.milestone.due_date).getTime() - new Date(b.milestone.due_date).getTime(),
    );
    paymentsList.sort(
      (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
    );

    return {
      activeCount: projects.filter((p) => p.status.toLowerCase() === "active").length,
      dueSoonCount: due7d,
      paidTotal: totalPaid.toFixed(2),
      needsAction: actions,
      upcomingMilestones: upcoming.slice(0, 5),
      recentPayments: paymentsList.slice(0, 5),
      projectMeta: meta,
    };
  }, [projects, milestoneQueries, paymentQueries, user?.role]);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <Skeleton className="h-44" />
          <Skeleton className="h-44" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <ErrorState
        message={error instanceof Error ? error.message : "Could not load dashboard."}
        onRetry={() => void refetch()}
      />
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-ink-900">
            Welcome back, {user?.name}
          </h1>
          <p className="mt-0.5 text-sm text-ink-600">
            Track project agreements, deliverable reviews, and milestone payments.
          </p>
        </div>
        {user?.role === "client" && (
          <Link to="/projects/new">
            <Button icon={<Plus className="h-4 w-4" />}>New project</Button>
          </Link>
        )}
      </div>

      {/* Stat cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <p className="text-xs font-medium text-ink-500">Active projects</p>
          <p className="mt-1 text-2xl font-bold tabular-nums text-ink-900">{activeCount}</p>
          <p className="mt-1 text-xs text-ink-600">{projects.length} total projects</p>
        </Card>
        <Card>
          <p className="text-xs font-medium text-ink-500">Milestones due in 7 days</p>
          <p className="mt-1 text-2xl font-bold tabular-nums text-ink-900">{dueSoonCount}</p>
          <p className="mt-1 text-xs text-ink-600">Unpaid upcoming deadlines</p>
        </Card>
        <Card>
          <p className="text-xs font-medium text-ink-500">Awaiting your action</p>
          <p className="mt-1 text-2xl font-bold tabular-nums text-brand-600">
            {needsAction.length}
          </p>
          <p className="mt-1 text-xs text-ink-600">Reviews, submissions, or payments</p>
        </Card>
        <Card>
          <p className="text-xs font-medium text-ink-500">Paid to date</p>
          <p className="mt-1 text-2xl font-bold text-success-600">
            <MoneyText value={paidTotal} />
          </p>
          <p className="mt-1 text-xs text-ink-600">Completed PayPal captures</p>
        </Card>
      </div>

      {projects.length === 0 ? (
        <EmptyState
          icon={<FolderKanban className="h-6 w-6" />}
          title="No projects yet"
          description={
            user?.role === "client"
              ? "Describe your first project to create an agreement and invite your freelancer."
              : "You have not been assigned to any projects yet. Share your user ID with a client so they can assign you."
          }
          action={
            user?.role === "client" ? (
              <Link to="/projects/new">
                <Button icon={<Plus className="h-4 w-4" />}>Create your first project</Button>
              </Link>
            ) : (
              <Link to="/profile">
                <Button variant="secondary">View my Freelancer ID (#{user?.id})</Button>
              </Link>
            )
          }
        />
      ) : (
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Left 2 cols: Needs action + Projects */}
          <div className="space-y-6 lg:col-span-2">
            <Card>
              <div className="flex items-center justify-between">
                <h2 className="text-base font-semibold text-ink-900">Needs your action</h2>
                <Badge tone={needsAction.length > 0 ? "brand" : "gray"}>
                  {needsAction.length}
                </Badge>
              </div>
              {needsAction.length === 0 ? (
                <p className="mt-3 flex items-center gap-2 text-sm text-ink-600">
                  <CheckCircle2 className="h-4 w-4 text-success-600" />
                  You are all caught up across active projects.
                </p>
              ) : (
                <ul className="mt-3 divide-y divide-ink-300/60">
                  {needsAction.slice(0, 5).map((item, idx) => (
                    <li
                      key={`${item.projectId}-${idx}`}
                      className="flex flex-wrap items-center justify-between gap-3 py-3 first:pt-0 last:pb-0"
                    >
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-ink-900">{item.label}</p>
                        <p className="text-xs text-ink-500">{item.projectTitle}</p>
                      </div>
                      <Link to={item.to}>
                        <Button size="sm" variant="secondary" icon={<ArrowRight className="h-3.5 w-3.5" />}>
                          {item.cta}
                        </Button>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </Card>

            <div className="space-y-3">
              <h2 className="text-base font-semibold text-ink-900">Your projects</h2>
              <div className="grid gap-4 sm:grid-cols-2">
                {projects.map((project) => {
                  const info = projectMeta.get(project.id);
                  const totalMilestones = info?.milestones.length ?? 0;
                  const paidMilestones = info?.paidCount ?? 0;
                  const pct =
                    totalMilestones > 0 ? Math.round((paidMilestones / totalMilestones) * 100) : 0;

                  return (
                    <Card key={project.id} className="flex flex-col justify-between gap-4">
                      <div className="space-y-2">
                        <div className="flex items-start justify-between gap-2">
                          <Link
                            to={`/projects/${project.id}`}
                            className="text-base font-semibold text-ink-900 hover:text-brand-600"
                          >
                            {project.title}
                          </Link>
                          <StatusBadge status={project.status} />
                        </div>
                        <p className="line-clamp-2 text-xs text-ink-600">{project.description}</p>
                      </div>

                      <div className="space-y-2.5 border-t border-ink-300/60 pt-3">
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-ink-600">
                            Budget: <MoneyText value={project.budget} currency={project.currency} className="text-ink-900" />
                          </span>
                          <span className="text-ink-600">
                            {paidMilestones}/{totalMilestones} milestones paid
                          </span>
                        </div>
                        <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
                          <div
                            className="h-full rounded-full bg-success-600 transition-all"
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                        <div className="flex items-center justify-between pt-1">
                          <span className="text-[11px] text-ink-500">
                            {project.freelancer_id
                              ? `Freelancer #${project.freelancer_id}`
                              : "No freelancer assigned"}
                          </span>
                          <Link
                            to={`/projects/${project.id}`}
                            className="text-xs font-semibold text-brand-600 hover:underline"
                          >
                            Open project →
                          </Link>
                        </div>
                      </div>
                    </Card>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Right column: Upcoming deadlines + Recent payments */}
          <div className="space-y-6">
            <Card>
              <div className="flex items-center gap-2">
                <CalendarClock className="h-4 w-4 text-brand-600" aria-hidden="true" />
                <h2 className="text-base font-semibold text-ink-900">Upcoming deadlines</h2>
              </div>
              {upcomingMilestones.length === 0 ? (
                <p className="mt-3 text-xs text-ink-600">No open milestone deadlines.</p>
              ) : (
                <ul className="mt-3 space-y-3">
                  {upcomingMilestones.map(({ projectId, projectTitle, milestone, overdue }) => (
                    <li key={milestone.id} className="flex items-start justify-between gap-2 text-xs">
                      <div className="min-w-0">
                        <Link
                          to={`/projects/${projectId}/milestones/${milestone.id}`}
                          className="font-medium text-ink-900 hover:text-brand-600"
                        >
                          {milestone.title}
                        </Link>
                        <p className="truncate text-ink-500">{projectTitle}</p>
                      </div>
                      <span
                        className={`shrink-0 font-medium ${
                          overdue ? "text-danger-600" : "text-ink-600"
                        }`}
                      >
                        {formatDate(milestone.due_date)}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </Card>

            <Card>
              <div className="flex items-center gap-2">
                <CreditCard className="h-4 w-4 text-success-600" aria-hidden="true" />
                <h2 className="text-base font-semibold text-ink-900">Recent payments</h2>
              </div>
              {recentPayments.length === 0 ? (
                <p className="mt-3 text-xs text-ink-600">No payments recorded yet.</p>
              ) : (
                <ul className="mt-3 space-y-3">
                  {recentPayments.map((pay) => (
                    <li key={pay.id} className="flex items-center justify-between gap-2 text-xs">
                      <div className="min-w-0">
                        <Link
                          to={`/projects/${pay.projectId}/payments`}
                          className="font-medium text-ink-900 hover:text-brand-600"
                        >
                          {pay.milestoneTitle}
                        </Link>
                        <p className="truncate text-ink-500">{pay.projectTitle}</p>
                      </div>
                      <div className="text-right">
                        <MoneyText value={pay.amount} className="block text-ink-900" />
                        <StatusBadge status={pay.status} className="mt-0.5" />
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}

