import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Plus, ShieldCheck, Trash2, XCircle } from "lucide-react";
import { api } from "../../api/endpoints";
import type { AgreementContent, AgreementPlannedMilestone } from "../../api/types";
import { ProjectLayout } from "../../components/layout/ProjectLayout";
import {
  AiChip,
  Badge,
  Button,
  Card,
  ConfirmDialog,
  DateInput,
  EmptyState,
  Input,
  MoneyInput,
  MoneyText,
  StatusBadge,
  Textarea,
  useToast,
} from "../../components/ui";
import {
  centsToDecimalString,
  formatDateTime,
  parseMoneyCents,
  toIsoUtcEndOfDay,
} from "../../lib/format";

export function AgreementPage({ projectId }: { projectId: number }) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { pushToast } = useToast();

  const { data: agreements = [], isLoading } = useQuery({
    queryKey: ["agreements", projectId],
    queryFn: () => api.listAgreements(projectId),
  });

  const { data: milestones = [] } = useQuery({
    queryKey: ["milestones", projectId],
    queryFn: () => api.listMilestones(projectId),
  });

  const latest = agreements[0];

  const [title, setTitle] = useState("");
  const [summary, setSummary] = useState("");
  const [scopeInText, setScopeInText] = useState("");
  const [scopeOutText, setScopeOutText] = useState("");
  const [paymentTerms, setPaymentTerms] = useState(
    "Each milestone is paid via PayPal only after the client accepts the milestone deliverable.",
  );
  const [revisionPolicy, setRevisionPolicy] = useState("Two revision rounds per milestone.");
  const [planned, setPlanned] = useState<AgreementPlannedMilestone[]>([]);
  const [approveOpen, setApproveOpen] = useState(false);
  const [rejectOpen, setRejectOpen] = useState(false);

  useEffect(() => {
    if (!latest) return;
    const c = latest.content;
    setTitle(typeof c.title === "string" ? c.title : "");
    setSummary(typeof c.summary === "string" ? c.summary : "");
    setScopeInText(Array.isArray(c.scope_in) ? c.scope_in.join("\n") : "");
    setScopeOutText(Array.isArray(c.scope_out) ? c.scope_out.join("\n") : "");
    if (typeof c.payment_terms === "string") setPaymentTerms(c.payment_terms);
    if (typeof c.revision_policy === "string") setRevisionPolicy(c.revision_policy);
    setPlanned(Array.isArray(c.planned_milestones) ? c.planned_milestones : []);
  }, [latest]);

  const saveVersionMutation = useMutation({
    mutationFn: (totalAmount: string) => {
      const content: AgreementContent = {
        title: title.trim() || "Project Agreement",
        summary: summary.trim(),
        scope_in: scopeInText
          .split("\n")
          .map((s) => s.trim())
          .filter(Boolean),
        scope_out: scopeOutText
          .split("\n")
          .map((s) => s.trim())
          .filter(Boolean),
        payment_terms: paymentTerms.trim(),
        revision_policy: revisionPolicy.trim(),
        total_amount: totalAmount,
        origin: "MANUAL",
        planned_milestones: planned,
      };
      return api.createAgreement(projectId, content);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["agreements", projectId] });
      pushToast({ tone: "success", title: "Agreement version saved" });
    },
    onError: (err) => {
      pushToast({
        tone: "error",
        title: "Could not save agreement",
        description: err instanceof Error ? err.message : undefined,
      });
    },
  });

  const approveMutation = useMutation({
    mutationFn: ({ agreementId, approved }: { agreementId: number; approved: boolean }) =>
      api.approveAgreement(agreementId, approved),
    onSuccess: (updated) => {
      void queryClient.invalidateQueries({ queryKey: ["agreements", projectId] });
      void queryClient.invalidateQueries({ queryKey: ["project", projectId] });
      setApproveOpen(false);
      setRejectOpen(false);
      pushToast({
        tone: updated.status === "rejected" ? "info" : "success",
        title:
          updated.status === "approved"
            ? "Agreement approved by both parties — project is now Active!"
            : updated.status === "rejected"
              ? "Changes requested on agreement"
              : "Your approval has been recorded",
      });
    },
    onError: (err) => {
      pushToast({
        tone: "error",
        title: "Approval action failed",
        description: err instanceof Error ? err.message : undefined,
      });
    },
  });

  const syncMilestonesMutation = useMutation({
    mutationFn: async () => {
      for (const item of planned) {
        await api.createMilestone(projectId, {
          title: item.title,
          description: item.description || item.title,
          amount: Number.parseFloat(item.amount).toFixed(2),
          due_date: toIsoUtcEndOfDay(item.due_date),
          acceptance_criteria:
            item.acceptance_criteria.length > 0
              ? item.acceptance_criteria
              : ["Deliverable meets agreed scope"],
        });
      }
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["milestones", projectId] });
      pushToast({ tone: "success", title: "Milestones created from agreement plan" });
      navigate(`/projects/${projectId}`);
    },
    onError: (err) => {
      pushToast({
        tone: "error",
        title: "Could not sync milestones",
        description: err instanceof Error ? err.message : undefined,
      });
    },
  });

  return (
    <ProjectLayout projectId={projectId} activeTab="agreement">
      {({ project, viewerRole }) => {
        const budgetCents = parseMoneyCents(project.budget);
        const plannedCents = planned.reduce((acc, m) => acc + parseMoneyCents(m.amount), 0);
        const diffCents = budgetCents - plannedCents;
        const balanced = planned.length === 0 || diffCents === 0;

        const isDraftProject = project.status.toLowerCase() === "draft";
        const latestIsDraft = latest?.status.toLowerCase() === "draft";
        const latestIsApproved = latest?.status.toLowerCase() === "approved";

        const userAlreadyApproved =
          latest &&
          ((viewerRole === "CLIENT" && Boolean(latest.client_approved_at)) ||
            (viewerRole === "FREELANCER" && Boolean(latest.freelancer_approved_at)));

        function autoBalance() {
          if (planned.length === 0) return;
          const total = parseMoneyCents(project.budget);
          const each = Math.floor(total / planned.length);
          const remainder = total - each * planned.length;
          setPlanned(
            planned.map((m, idx) => ({
              ...m,
              amount: centsToDecimalString(idx === planned.length - 1 ? each + remainder : each),
            })),
          );
        }

        if (isLoading) {
          return <Card>Loading agreement…</Card>;
        }

        return (
          <div className="grid gap-6 lg:grid-cols-3">
            <div className="space-y-6 lg:col-span-2">
              {!latest && viewerRole === "FREELANCER" ? (
                <EmptyState
                  title="No agreement drafted yet"
                  description="The client is preparing the initial agreement draft."
                />
              ) : (
                <Card className="space-y-5">
                  <div className="flex flex-wrap items-center justify-between gap-3 border-b border-ink-300/60 pb-4">
                    <div className="flex flex-wrap items-center gap-2">
                      <h2 className="text-lg font-semibold text-ink-900">
                        {latest ? `Agreement v${latest.version}` : "Create initial agreement"}
                      </h2>
                      {latest && <StatusBadge status={latest.status} context="agreement" />}
                      <AiChip label="Editable scope & criteria" />
                    </div>
                    {latestIsDraft && !userAlreadyApproved && (
                      <div className="flex flex-wrap gap-2">
                        {viewerRole === "FREELANCER" && (
                          <Button
                            size="sm"
                            variant="secondary"
                            icon={<XCircle className="h-4 w-4 text-danger-600" />}
                            onClick={() => setRejectOpen(true)}
                          >
                            Request changes
                          </Button>
                        )}
                        <Button
                          size="sm"
                          icon={<CheckCircle2 className="h-4 w-4" />}
                          onClick={() => setApproveOpen(true)}
                        >
                          Approve agreement
                        </Button>
                      </div>
                    )}
                  </div>

                  {/* Read-only if approved or freelancer viewing draft */}
                  {latestIsApproved || viewerRole === "FREELANCER" ? (
                    <div className="space-y-5 text-sm">
                      <div>
                        <p className="text-xs font-semibold uppercase text-ink-500">Title</p>
                        <p className="mt-1 font-semibold text-ink-900">
                          {title || project.title}
                        </p>
                      </div>
                      <div>
                        <p className="text-xs font-semibold uppercase text-ink-500">Summary</p>
                        <p className="mt-1 whitespace-pre-wrap text-ink-700">
                          {summary || project.description}
                        </p>
                      </div>
                      <div className="grid gap-4 sm:grid-cols-2">
                        <div>
                          <p className="text-xs font-semibold uppercase text-ink-500">In scope</p>
                          <ul className="mt-1 list-disc space-y-1 pl-4 text-ink-700">
                            {scopeInText
                              .split("\n")
                              .filter(Boolean)
                              .map((item, i) => (
                                <li key={i}>{item}</li>
                              ))}
                          </ul>
                        </div>
                        <div>
                          <p className="text-xs font-semibold uppercase text-ink-500">
                            Out of scope
                          </p>
                          <ul className="mt-1 list-disc space-y-1 pl-4 text-ink-700">
                            {scopeOutText
                              .split("\n")
                              .filter(Boolean)
                              .map((item, i) => (
                                <li key={i}>{item}</li>
                              ))}
                          </ul>
                        </div>
                      </div>
                      <div className="grid gap-4 sm:grid-cols-2">
                        <div>
                          <p className="text-xs font-semibold uppercase text-ink-500">
                            Payment terms
                          </p>
                          <p className="mt-1 text-ink-700">{paymentTerms}</p>
                        </div>
                        <div>
                          <p className="text-xs font-semibold uppercase text-ink-500">
                            Revision policy
                          </p>
                          <p className="mt-1 text-ink-700">{revisionPolicy}</p>
                        </div>
                      </div>

                      {planned.length > 0 && (
                        <div className="space-y-2 border-t border-ink-300/60 pt-4">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <p className="text-xs font-semibold uppercase text-ink-500">
                              Planned milestones
                            </p>
                            {latestIsApproved &&
                              viewerRole === "CLIENT" &&
                              milestones.length === 0 && (
                                <Button
                                  size="sm"
                                  loading={syncMilestonesMutation.isPending}
                                  onClick={() => syncMilestonesMutation.mutate()}
                                >
                                  Create these {planned.length} milestones
                                </Button>
                              )}
                          </div>
                          <div className="space-y-2">
                            {planned.map((m, idx) => (
                              <div
                                key={idx}
                                className="rounded-lg border border-ink-300/70 bg-canvas p-3"
                              >
                                <div className="flex items-center justify-between">
                                  <span className="font-semibold text-ink-900">
                                    {idx + 1}. {m.title}
                                  </span>
                                  <MoneyText value={m.amount} />
                                </div>
                                <p className="mt-1 text-xs text-ink-600">{m.description}</p>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    /* Client Editor */
                    <div className="space-y-5">
                      <Input
                        id="ag-title"
                        label="Agreement title"
                        value={title}
                        onChange={(e) => setTitle(e.target.value)}
                      />
                      <Textarea
                        id="ag-summary"
                        label="Project summary"
                        rows={3}
                        value={summary}
                        onChange={(e) => setSummary(e.target.value)}
                      />
                      <div className="grid gap-4 sm:grid-cols-2">
                        <Textarea
                          id="ag-scope-in"
                          label="In scope (one item per line)"
                          rows={4}
                          value={scopeInText}
                          onChange={(e) => setScopeInText(e.target.value)}
                        />
                        <Textarea
                          id="ag-scope-out"
                          label="Out of scope (one item per line)"
                          rows={4}
                          value={scopeOutText}
                          onChange={(e) => setScopeOutText(e.target.value)}
                        />
                      </div>
                      <div className="grid gap-4 sm:grid-cols-2">
                        <Textarea
                          id="ag-pay-terms"
                          label="Payment terms"
                          rows={2}
                          value={paymentTerms}
                          onChange={(e) => setPaymentTerms(e.target.value)}
                        />
                        <Textarea
                          id="ag-rev-policy"
                          label="Revision policy"
                          rows={2}
                          value={revisionPolicy}
                          onChange={(e) => setRevisionPolicy(e.target.value)}
                        />
                      </div>

                      {/* Planned milestones + budget reconciler */}
                      <div className="space-y-3 border-t border-ink-300/60 pt-4">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <div>
                            <h3 className="text-sm font-semibold text-ink-900">
                              Planned milestone breakdown
                            </h3>
                            <p
                              className={`text-xs font-medium ${
                                balanced ? "text-success-700" : "text-danger-600"
                              }`}
                            >
                              Allocated {centsToDecimalString(plannedCents)} of{" "}
                              {centsToDecimalString(budgetCents)} USD
                              {!balanced &&
                                ` (${centsToDecimalString(Math.abs(diffCents))} ${
                                  diffCents > 0 ? "unallocated" : "over budget"
                                })`}
                            </p>
                          </div>
                          <div className="flex gap-2">
                            {planned.length > 0 && !balanced && (
                              <Button size="sm" variant="secondary" onClick={autoBalance}>
                                Auto-balance
                              </Button>
                            )}
                            <Button
                              size="sm"
                              variant="secondary"
                              icon={<Plus className="h-3.5 w-3.5" />}
                              onClick={() =>
                                setPlanned((prev) => [
                                  ...prev,
                                  {
                                    title: `Milestone ${prev.length + 1}`,
                                    description: "",
                                    amount: "100.00",
                                    due_date: new Date(Date.now() + (prev.length + 1) * 7 * 86400_000)
                                      .toISOString()
                                      .slice(0, 10),
                                    acceptance_criteria: ["Deliverable meets agreed scope"],
                                  },
                                ])
                              }
                            >
                              Add milestone
                            </Button>
                          </div>
                        </div>

                        {planned.map((m, idx) => (
                          <div
                            key={idx}
                            className="space-y-3 rounded-xl border border-ink-300/80 bg-canvas p-4"
                          >
                            <div className="flex items-center justify-between">
                              <span className="text-xs font-semibold uppercase text-ink-600">
                                Milestone {idx + 1}
                              </span>
                              <button
                                type="button"
                                aria-label={`Remove milestone ${idx + 1}`}
                                onClick={() =>
                                  setPlanned((prev) => prev.filter((_, i) => i !== idx))
                                }
                                className="rounded p-1 text-ink-500 hover:text-danger-600"
                              >
                                <Trash2 className="h-4 w-4" />
                              </button>
                            </div>
                            <Input
                              id={`pm-title-${idx}`}
                              label="Title"
                              value={m.title}
                              onChange={(e) => {
                                const val = e.target.value;
                                setPlanned((prev) =>
                                  prev.map((item, i) => (i === idx ? { ...item, title: val } : item)),
                                );
                              }}
                            />
                            <div className="grid gap-3 sm:grid-cols-2">
                              <MoneyInput
                                id={`pm-amt-${idx}`}
                                label="Amount"
                                value={m.amount}
                                onChange={(val) =>
                                  setPlanned((prev) =>
                                    prev.map((item, i) => (i === idx ? { ...item, amount: val } : item)),
                                  )
                                }
                              />
                              <DateInput
                                id={`pm-due-${idx}`}
                                label="Due date"
                                value={m.due_date}
                                onChange={(e) => {
                                  const val = e.target.value;
                                  setPlanned((prev) =>
                                    prev.map((item, i) =>
                                      i === idx ? { ...item, due_date: val } : item,
                                    ),
                                  );
                                }}
                              />
                            </div>
                            <Textarea
                              id={`pm-crit-${idx}`}
                              label="Acceptance criteria (one per line)"
                              rows={2}
                              value={m.acceptance_criteria.join("\n")}
                              onChange={(e) => {
                                const list = e.target.value.split("\n");
                                setPlanned((prev) =>
                                  prev.map((item, i) =>
                                    i === idx ? { ...item, acceptance_criteria: list } : item,
                                  ),
                                );
                              }}
                            />
                          </div>
                        ))}
                      </div>

                      {isDraftProject && (
                        <div className="flex flex-wrap justify-end gap-2 border-t border-ink-300/60 pt-4">
                          <Button
                            loading={saveVersionMutation.isPending}
                            disabled={!balanced}
                            onClick={() => saveVersionMutation.mutate(project.budget)}
                          >
                            {latest ? "Save as new agreement version" : "Save draft agreement"}
                          </Button>
                        </div>
                      )}
                    </div>
                  )}
                </Card>
              )}
            </div>

            {/* Right sidebar: Dual approval status + version history */}
            <div className="space-y-6">
              <Card className="space-y-3">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="h-5 w-5 text-brand-600" aria-hidden="true" />
                  <h2 className="text-base font-semibold text-ink-900">Dual approval status</h2>
                </div>
                {latest ? (
                  <div className="space-y-2.5 text-sm">
                    <div className="flex items-center justify-between rounded-lg bg-canvas px-3 py-2">
                      <span className="font-medium text-ink-700">Client approval</span>
                      {latest.client_approved_at ? (
                        <Badge tone="success">
                          Approved {formatDateTime(latest.client_approved_at)}
                        </Badge>
                      ) : (
                        <Badge tone="warning">Pending</Badge>
                      )}
                    </div>
                    <div className="flex items-center justify-between rounded-lg bg-canvas px-3 py-2">
                      <span className="font-medium text-ink-700">Freelancer approval</span>
                      {latest.freelancer_approved_at ? (
                        <Badge tone="success">
                          Approved {formatDateTime(latest.freelancer_approved_at)}
                        </Badge>
                      ) : (
                        <Badge tone="warning">Pending</Badge>
                      )}
                    </div>
                    {!project.freelancer_id && (
                      <p className="text-xs text-warning-700">
                        Assign a freelancer on the Overview tab so both parties can approve.
                      </p>
                    )}
                  </div>
                ) : (
                  <p className="text-xs text-ink-600">Save a draft agreement to begin approval.</p>
                )}
              </Card>

              <Card className="space-y-3">
                <h2 className="text-base font-semibold text-ink-900">Version history</h2>
                {agreements.length === 0 ? (
                  <p className="text-xs text-ink-600">No saved versions yet.</p>
                ) : (
                  <ul className="space-y-2">
                    {agreements.map((ag) => (
                      <li
                        key={ag.id}
                        className="flex items-center justify-between rounded-lg border border-ink-300/60 px-3 py-2 text-xs"
                      >
                        <span className="font-semibold text-ink-900">Version {ag.version}</span>
                        <StatusBadge status={ag.status} context="agreement" />
                      </li>
                    ))}
                  </ul>
                )}
              </Card>
            </div>

            <ConfirmDialog
              open={approveOpen}
              onClose={() => setApproveOpen(false)}
              onConfirm={() => {
                if (latest) approveMutation.mutate({ agreementId: latest.id, approved: true });
              }}
              loading={approveMutation.isPending}
              title={`Approve Agreement v${latest?.version ?? ""}`}
              message={`Confirm approval of "${title || project.title}" for ${centsToDecimalString(
                budgetCents,
              )} USD. Once both client and freelancer approve, the project becomes Active.`}
              confirmLabel="Approve agreement"
            />

            <ConfirmDialog
              open={rejectOpen}
              onClose={() => setRejectOpen(false)}
              onConfirm={() => {
                if (latest) approveMutation.mutate({ agreementId: latest.id, approved: false });
              }}
              loading={approveMutation.isPending}
              danger
              title="Request changes on agreement"
              message="This marks the current draft as needing changes so the client can save a revised version."
              confirmLabel="Request changes"
            />
          </div>
        );
      }}
    </ProjectLayout>
  );
}

