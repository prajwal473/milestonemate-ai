import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Bot, CreditCard, FileCheck2, ShieldCheck, User } from "lucide-react";
import { api } from "../../api/endpoints";
import { getPaymentApi } from "../../api/paymentsAdapter";
import type { ActivityEvent } from "../../api/types";
import { ProjectLayout } from "../../components/layout/ProjectLayout";
import { Badge, Button, Card, Copyable, EmptyState } from "../../components/ui";
import { formatDateTime } from "../../lib/format";

export function ActivityPage({ projectId }: { projectId: number }) {
  const paymentApi = getPaymentApi();
  const [filter, setFilter] = useState<"all" | "agreement" | "deliverable" | "payment">("all");

  const { data: project } = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => api.getProject(projectId),
  });
  const { data: agreements = [] } = useQuery({
    queryKey: ["agreements", projectId],
    queryFn: () => api.listAgreements(projectId),
  });
  const { data: milestones = [] } = useQuery({
    queryKey: ["milestones", projectId],
    queryFn: () => api.listMilestones(projectId),
  });
  const { data: ledger } = useQuery({
    queryKey: ["project-payments", projectId],
    queryFn: () => paymentApi.getProjectPayments(String(projectId)),
  });

  const events = useMemo<ActivityEvent[]>(() => {
    const list: ActivityEvent[] = [];

    if (project) {
      list.push({
        id: `proj-${project.id}`,
        category: "project",
        actorType: "USER",
        action: "Project created",
        description: `${project.title} (${project.budget} ${project.currency})`,
        createdAt: project.created_at,
      });
    }

    agreements.forEach((ag) => {
      if (ag.client_approved_at) {
        list.push({
          id: `ag-client-${ag.id}`,
          category: "agreement",
          actorType: "USER",
          action: `Client approved Agreement v${ag.version}`,
          description: `Agreement status: ${ag.status}`,
          createdAt: ag.client_approved_at,
        });
      }
      if (ag.freelancer_approved_at) {
        list.push({
          id: `ag-free-${ag.id}`,
          category: "agreement",
          actorType: "USER",
          action: `Freelancer approved Agreement v${ag.version}`,
          description: `Agreement status: ${ag.status}`,
          createdAt: ag.freelancer_approved_at,
        });
      }
    });

    milestones.forEach((ms) => {
      list.push({
        id: `ms-${ms.id}`,
        category: "deliverable",
        actorType: "SYSTEM",
        action: `Milestone "${ms.title}"`,
        description: `Current status: ${ms.status} · Amount: ${ms.amount} USD`,
        createdAt: ms.due_date,
      });
    });

    (ledger?.items ?? []).forEach((pay) => {
      (pay.events ?? []).forEach((ev, idx) => {
        list.push({
          id: `pay-${pay.id}-${idx}`,
          category: "payment",
          actorType: ev.source === "WEBHOOK" ? "PAYPAL" : "USER",
          action: ev.event_type.replaceAll("_", " "),
          description: `${pay.milestone_title ?? `Milestone #${pay.milestone_id}`} · ${ev.from_status ?? "INIT"} → ${ev.to_status ?? pay.status}`,
          createdAt: ev.created_at,
          reference: ev.paypal_ref,
        });
      });
    });

    return list.sort(
      (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
    );
  }, [project, agreements, milestones, ledger]);

  const filtered = events.filter((e) => (filter === "all" ? true : e.category === filter));

  return (
    <ProjectLayout projectId={projectId} activeTab="activity">
      {() => (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <Badge tone="success" dot>
              <ShieldCheck className="h-3.5 w-3.5" aria-hidden="true" />
              Project activity &amp; payment audit trail
            </Badge>

            <div className="flex flex-wrap gap-1.5">
              {(["all", "agreement", "deliverable", "payment"] as const).map((tab) => (
                <Button
                  key={tab}
                  size="sm"
                  variant={filter === tab ? "primary" : "secondary"}
                  onClick={() => setFilter(tab)}
                >
                  {tab === "all" ? "All" : `${tab[0].toUpperCase()}${tab.slice(1)}s`}
                </Button>
              ))}
            </div>
          </div>

          {filtered.length === 0 ? (
            <EmptyState
              title="No activity recorded yet"
              description="Actions on agreements, milestones, deliverables, and payments appear here."
            />
          ) : (
            <Card>
              <ol className="space-y-4">
                {filtered.map((ev) => {
                  const Icon =
                    ev.actorType === "AI"
                      ? Bot
                      : ev.actorType === "PAYPAL"
                        ? CreditCard
                        : ev.category === "agreement"
                          ? FileCheck2
                          : User;
                  return (
                    <li
                      key={ev.id}
                      className="flex items-start gap-3 border-b border-ink-300/50 pb-4 last:border-b-0 last:pb-0"
                    >
                      <span className="mt-0.5 inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-50 text-brand-600">
                        <Icon className="h-4 w-4" aria-hidden="true" />
                      </span>
                      <div className="min-w-0 flex-1 space-y-1">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <p className="text-sm font-semibold text-ink-900">{ev.action}</p>
                          <span className="text-xs text-ink-500">
                            {formatDateTime(ev.createdAt)}
                          </span>
                        </div>
                        <p className="text-xs text-ink-600">{ev.description}</p>
                        {ev.reference && <Copyable value={ev.reference} label="Ref" />}
                      </div>
                    </li>
                  );
                })}
              </ol>
            </Card>
          )}
        </div>
      )}
    </ProjectLayout>
  );
}

