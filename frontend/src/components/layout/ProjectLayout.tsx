import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../../api/endpoints";
import type { Project } from "../../api/types";
import { useAuth } from "../../features/auth/useAuth";
import { formatMoney } from "../../lib/format";
import { Badge, ErrorState, Skeleton, StatusBadge, Tabs } from "../ui";

interface ProjectLayoutProps {
  projectId: number;
  activeTab: "overview" | "agreement" | "milestones" | "payments" | "activity";
  children: (ctx: { project: Project; viewerRole: "CLIENT" | "FREELANCER" }) => ReactNode;
}

export function ProjectLayout({ projectId, activeTab, children }: ProjectLayoutProps) {
  const { user } = useAuth();

  const {
    data: project,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => api.getProject(projectId),
    enabled: Number.isFinite(projectId) && projectId > 0,
  });

  const { data: milestones = [] } = useQuery({
    queryKey: ["milestones", projectId],
    queryFn: () => api.listMilestones(projectId),
    enabled: Number.isFinite(projectId) && projectId > 0,
  });

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-80" />
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (error || !project) {
    return (
      <ErrorState
        message={error instanceof Error ? error.message : "Could not load this project."}
        onRetry={() => void refetch()}
      />
    );
  }

  const viewerRole: "CLIENT" | "FREELANCER" =
    user?.id === project.client_id || user?.role === "client" ? "CLIENT" : "FREELANCER";

  const tabs = [
    { id: "overview", label: "Overview", to: `/projects/${projectId}` },
    { id: "agreement", label: "Agreement", to: `/projects/${projectId}/agreement` },
    {
      id: "milestones",
      label: "Milestones",
      to:
        milestones.length > 0
          ? `/projects/${projectId}/milestones/${milestones[0].id}`
          : `/projects/${projectId}#milestones`,
      count: milestones.length,
    },
    { id: "payments", label: "Payments", to: `/projects/${projectId}/payments` },
    { id: "activity", label: "Activity", to: `/projects/${projectId}/activity` },
  ];

  return (
    <div className="space-y-6">
      <div>
        <Link
          to="/dashboard"
          className="inline-flex items-center gap-1.5 text-xs font-medium text-ink-600 hover:text-brand-600"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to dashboard
        </Link>

        <div className="mt-2 flex flex-wrap items-start justify-between gap-4">
          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center gap-2.5">
              <h1 className="text-2xl font-bold tracking-tight text-ink-900">{project.title}</h1>
              <StatusBadge status={project.status} />
              <Badge tone={viewerRole === "CLIENT" ? "brand" : "ai"}>
                Your role: {viewerRole === "CLIENT" ? "Client" : "Freelancer"}
              </Badge>
            </div>
            <p className="max-w-3xl text-sm text-ink-600">{project.description}</p>
          </div>

          <div className="rounded-xl border border-ink-300/70 bg-surface px-4 py-3 text-right shadow-sm">
            <p className="text-xs font-medium text-ink-500">Project budget</p>
            <p className="text-lg font-bold tabular-nums text-ink-900">
              {formatMoney(project.budget, project.currency)}
            </p>
          </div>
        </div>
      </div>

      <Tabs items={tabs} activeId={activeTab} />

      <div>{children({ project, viewerRole })}</div>
    </div>
  );
}

