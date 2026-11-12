import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CheckCircle2,
  ExternalLink,
  Plus,
  Sparkles,
  Trash2,
  XCircle,
} from "lucide-react";
import { api, getCachedEvaluation } from "../../api/endpoints";
import { getPaymentApi } from "../../api/paymentsAdapter";
import type { Evaluation } from "../../api/types";
import { ProjectLayout } from "../../components/layout/ProjectLayout";
import {
  AiChip,
  Badge,
  Button,
  Card,
  ConfirmDialog,
  DateText,
  EmptyState,
  ErrorState,
  FileDropzone,
  Input,
  MoneyText,
  Skeleton,
  StatusBadge,
  Textarea,
  useToast,
} from "../../components/ui";
import { PayMilestoneCard } from "../payments/PayMilestoneCard";
import { formatDateTime } from "../../lib/format";

function EvaluationSection({
  deliverableId,
  viewerRole,
  milestoneStatus,
  onDecisionDone,
}: {
  deliverableId: number;
  viewerRole: "CLIENT" | "FREELANCER";
  milestoneStatus: string;
  onDecisionDone: () => void;
}) {
  const { pushToast } = useToast();
  const [evaluation, setEvaluation] = useState<Evaluation | null>(() =>
    getCachedEvaluation(deliverableId),
  );
  const [evalError, setEvalError] = useState<string | null>(null);
  const [decisionConfirm, setDecisionConfirm] = useState<"accepted" | "revision_requested" | null>(
    null,
  );

  const evaluateMutation = useMutation({
    mutationFn: () => api.evaluateDeliverable(deliverableId),
    onSuccess: (res) => {
      setEvalError(null);
      setEvaluation(res);
      pushToast({ tone: "success", title: "AI evaluation completed" });
    },
    onError: (err) => {
      const msg = err instanceof Error ? err.message : "AI evaluation failed.";
      setEvalError(msg);
      pushToast({ tone: "error", title: "Evaluation failed", description: msg });
    },
  });

  const decisionMutation = useMutation({
    mutationFn: ({
      evaluationId,
      decision,
    }: {
      evaluationId: number;
      decision: "accepted" | "revision_requested";
    }) => api.submitEvaluationDecision(evaluationId, decision),
    onSuccess: (res) => {
      setEvaluation(res);
      setDecisionConfirm(null);
      onDecisionDone();
      pushToast({
        tone: res.human_decision === "accepted" ? "success" : "info",
        title:
          res.human_decision === "accepted"
            ? "Milestone accepted — ready for PayPal payment"
            : "Revision requested from freelancer",
      });
    },
    onError: (err) => {
      pushToast({
        tone: "error",
        title: "Decision failed",
        description: err instanceof Error ? err.message : undefined,
      });
    },
  });

  const awaitingDecision = milestoneStatus.toLowerCase() === "submitted";

  return (
    <Card className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <h3 className="text-base font-semibold text-ink-900">AI Deliverable Evaluation</h3>
          <AiChip label="Advisory only" />
        </div>
        {viewerRole === "CLIENT" && awaitingDecision && !evaluation && (
          <Button
            size="sm"
            loading={evaluateMutation.isPending}
            icon={<Sparkles className="h-4 w-4" />}
            onClick={() => evaluateMutation.mutate()}
          >
            Run AI evaluation
          </Button>
        )}
      </div>

      {evalError && (
        <ErrorState
          message={evalError}
          onRetry={viewerRole === "CLIENT" ? () => evaluateMutation.mutate() : undefined}
        />
      )}

      {!evaluation && !evalError && (
        <p className="text-sm text-ink-600">
          {viewerRole === "CLIENT"
            ? 'Click "Run AI evaluation" to assess this submission against the milestone acceptance criteria. You always make the final decision.'
            : "Waiting for the client to run AI evaluation and record their acceptance decision."}
        </p>
      )}

      {evaluation && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-ink-300/70 bg-canvas p-3.5">
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge status={evaluation.recommendation} />
              {evaluation.score !== null && (
                <Badge tone="brand">Score: {String(evaluation.score)} / 100</Badge>
              )}
              {evaluation.model_name && (
                <span className="font-mono text-xs text-ink-500">{evaluation.model_name}</span>
              )}
            </div>
            {evaluation.human_decision && (
              <StatusBadge status={evaluation.human_decision} />
            )}
          </div>

          {evaluation.findings.summary && (
            <p className="text-sm text-ink-700">{evaluation.findings.summary}</p>
          )}

          {evaluation.findings.criteria_results && evaluation.findings.criteria_results.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase text-ink-500">
                Criteria assessment
              </p>
              <ul className="space-y-2">
                {evaluation.findings.criteria_results.map((cr, idx) => (
                  <li
                    key={idx}
                    className="rounded-lg border border-ink-300/70 bg-surface p-3 text-sm"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="font-medium text-ink-900">{cr.criterion}</span>
                      <StatusBadge status={cr.status} />
                    </div>
                    <p className="mt-1 text-xs text-ink-600">{cr.evidence}</p>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {evaluation.findings.missing_requirements &&
            evaluation.findings.missing_requirements.length > 0 && (
              <div className="rounded-lg border border-amber-200 bg-warning-50 p-3 text-xs text-warning-700">
                <p className="font-semibold">Missing requirements flagged</p>
                <ul className="mt-1 list-disc space-y-0.5 pl-4">
                  {evaluation.findings.missing_requirements.map((item, idx) => (
                    <li key={idx}>{item}</li>
                  ))}
                </ul>
              </div>
            )}

          <p className="text-xs text-ink-500">
            AI output is advisory only (not a guarantee). The client makes the final acceptance
            decision.
          </p>

          {viewerRole === "CLIENT" && awaitingDecision && !evaluation.human_decision && (
            <div className="flex flex-wrap items-center justify-end gap-2 border-t border-ink-300/60 pt-3">
              <Button
                variant="secondary"
                icon={<XCircle className="h-4 w-4 text-danger-600" />}
                onClick={() => setDecisionConfirm("revision_requested")}
              >
                Request revision
              </Button>
              <Button
                icon={<CheckCircle2 className="h-4 w-4" />}
                onClick={() => setDecisionConfirm("accepted")}
              >
                Accept milestone
              </Button>
            </div>
          )}
        </div>
      )}

      <ConfirmDialog
        open={decisionConfirm !== null}
        onClose={() => setDecisionConfirm(null)}
        onConfirm={() => {
          if (evaluation && decisionConfirm) {
            decisionMutation.mutate({
              evaluationId: evaluation.id,
              decision: decisionConfirm,
            });
          }
        }}
        loading={decisionMutation.isPending}
        danger={decisionConfirm === "revision_requested"}
        title={
          decisionConfirm === "accepted"
            ? "Accept this milestone?"
            : "Request revision on this deliverable?"
        }
        message={
          decisionConfirm === "accepted"
            ? "Accepting marks the milestone ready for PayPal checkout. No funds move until you complete PayPal approval."
            : "The freelancer will be able to submit an updated deliverable."
        }
        confirmLabel={decisionConfirm === "accepted" ? "Accept milestone" : "Request revision"}
      />
    </Card>
  );
}

export function MilestoneDetailPage({
  projectId,
  milestoneId,
}: {
  projectId: number;
  milestoneId: number;
}) {
  const queryClient = useQueryClient();
  const { pushToast } = useToast();
  const paymentApi = getPaymentApi();

  const [note, setNote] = useState("");
  const [linkInput, setLinkInput] = useState("");
  const [fileUrls, setFileUrls] = useState<string[]>([]);
  const [localFiles, setLocalFiles] = useState<File[]>([]);

  const {
    data: milestone,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ["milestone", milestoneId],
    queryFn: () => api.getMilestone(milestoneId),
  });

  const { data: deliverables = [] } = useQuery({
    queryKey: ["deliverables", milestoneId],
    queryFn: () => api.listDeliverables(milestoneId),
  });

  const submitMutation = useMutation({
    mutationFn: () => {
      const combinedNote =
        localFiles.length > 0
          ? `${note.trim()}\n\nAttached local files: ${localFiles.map((f) => f.name).join(", ")}`
          : note.trim();
      return api.submitDeliverable(milestoneId, {
        description: combinedNote,
        file_urls: fileUrls,
      });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["deliverables", milestoneId] });
      void queryClient.invalidateQueries({ queryKey: ["milestone", milestoneId] });
      void queryClient.invalidateQueries({ queryKey: ["milestones", projectId] });
      setNote("");
      setFileUrls([]);
      setLocalFiles([]);
      pushToast({ tone: "success", title: "Deliverable submitted for review" });
    },
    onError: (err) => {
      pushToast({
        tone: "error",
        title: "Submission failed",
        description: err instanceof Error ? err.message : undefined,
      });
    },
  });

  function addLink() {
    const trimmed = linkInput.trim();
    if (!trimmed) return;
    if (!/^https?:\/\//i.test(trimmed)) {
      pushToast({ tone: "error", title: "URL must start with http:// or https://" });
      return;
    }
    setFileUrls((prev) => [...prev, trimmed]);
    setLinkInput("");
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (note.trim().length < 10) {
      pushToast({
        tone: "error",
        title: "Please provide at least 10 characters describing your deliverable.",
      });
      return;
    }
    submitMutation.mutate();
  }

  return (
    <ProjectLayout projectId={projectId} activeTab="milestones">
      {({ viewerRole }) => {
        if (isLoading) {
          return (
            <div className="space-y-4">
              <Skeleton className="h-28" />
              <Skeleton className="h-64" />
            </div>
          );
        }

        if (error || !milestone) {
          return (
            <ErrorState
              message={error instanceof Error ? error.message : "Could not load milestone."}
              onRetry={() => void refetch()}
            />
          );
        }

        const statusLower = milestone.status.toLowerCase();
        const canSubmit =
          viewerRole === "FREELANCER" &&
          ["pending", "in_progress", "revision_requested"].includes(statusLower);
        const latestDeliverable = deliverables[0];

        return (
          <div className="space-y-6">
            {/* Milestone Header Card */}
            <Card className="flex flex-wrap items-start justify-between gap-4">
              <div className="space-y-1.5">
                <div className="flex flex-wrap items-center gap-2.5">
                  <h2 className="text-xl font-bold text-ink-900">{milestone.title}</h2>
                  <StatusBadge status={milestone.status} context="milestone" />
                </div>
                <p className="max-w-2xl text-sm text-ink-600">{milestone.description}</p>
              </div>
              <div className="text-right">
                <p className="text-xl font-bold text-ink-900">
                  <MoneyText value={milestone.amount} />
                </p>
                <p className="mt-0.5 text-xs text-ink-600">
                  Due <DateText value={milestone.due_date} />
                </p>
              </div>
            </Card>

            <div className="grid gap-6 lg:grid-cols-3">
              {/* Left column: Acceptance criteria + Submission history */}
              <div className="space-y-6">
                <Card className="space-y-3">
                  <h3 className="text-base font-semibold text-ink-900">Acceptance criteria</h3>
                  <ul className="space-y-2 text-sm text-ink-700">
                    {milestone.acceptance_criteria.map((criterion, idx) => (
                      <li
                        key={idx}
                        className="flex items-start gap-2 rounded-lg border border-ink-300/60 bg-canvas px-3 py-2"
                      >
                        <span className="mt-0.5 text-xs font-bold text-brand-600">{idx + 1}.</span>
                        <span>{criterion}</span>
                      </li>
                    ))}
                  </ul>
                </Card>

                <Card className="space-y-3">
                  <h3 className="text-base font-semibold text-ink-900">Submission history</h3>
                  {deliverables.length === 0 ? (
                    <p className="text-xs text-ink-600">No deliverables submitted yet.</p>
                  ) : (
                    <ul className="space-y-3">
                      {deliverables.map((del, idx) => (
                        <li
                          key={del.id}
                          className="space-y-2 rounded-lg border border-ink-300/70 bg-canvas p-3 text-xs"
                        >
                          <div className="flex items-center justify-between gap-2">
                            <span className="font-semibold text-ink-900">
                              Submission #{deliverables.length - idx}
                            </span>
                            <StatusBadge status={del.status} />
                          </div>
                          <p className="whitespace-pre-wrap text-ink-700">{del.description}</p>
                          {del.file_urls.length > 0 && (
                            <div className="space-y-1">
                              {del.file_urls.map((url, uIdx) => (
                                <a
                                  key={uIdx}
                                  href={url}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="flex items-center gap-1 text-brand-600 hover:underline"
                                >
                                  <ExternalLink className="h-3 w-3" />
                                  <span className="truncate">{url}</span>
                                </a>
                              ))}
                            </div>
                          )}
                          <p className="text-[11px] text-ink-500">
                            Submitted {formatDateTime(del.created_at)}
                          </p>
                        </li>
                      ))}
                    </ul>
                  )}
                </Card>
              </div>

              {/* Right 2 columns: Submit / Evaluation / Payment */}
              <div className="space-y-6 lg:col-span-2">
                {canSubmit && (
                  <Card>
                    <form onSubmit={handleSubmit} className="space-y-4">
                      <div>
                        <h3 className="text-base font-semibold text-ink-900">
                          {statusLower === "revision_requested"
                            ? "Resubmit milestone deliverable"
                            : "Submit milestone deliverable"}
                        </h3>
                        <p className="mt-0.5 text-xs text-ink-600">
                          Describe everything completed against the acceptance criteria so the AI
                          and client can verify your work.
                        </p>
                      </div>

                      <Textarea
                        id="deliverable-note"
                        label="Deliverable summary & evidence"
                        required
                        rows={5}
                        value={note}
                        onChange={(e) => setNote(e.target.value)}
                        placeholder="Summarize what you delivered, quote key sections, or paste test results..."
                      />

                      <div className="space-y-2">
                        <div className="flex flex-wrap items-end gap-2">
                          <div className="min-w-[200px] flex-1">
                            <Input
                              id="deliverable-link"
                              label="Deliverable link (optional)"
                              type="url"
                              value={linkInput}
                              onChange={(e) => setLinkInput(e.target.value)}
                              placeholder="https://github.com/... or https://preview..."
                            />
                          </div>
                          <Button
                            variant="secondary"
                            icon={<Plus className="h-4 w-4" />}
                            onClick={addLink}
                          >
                            Add link
                          </Button>
                        </div>

                        {fileUrls.length > 0 && (
                          <ul className="space-y-1">
                            {fileUrls.map((url, idx) => (
                              <li
                                key={idx}
                                className="flex items-center justify-between rounded-lg border border-ink-300/70 bg-canvas px-3 py-1.5 text-xs"
                              >
                                <span className="truncate text-brand-700">{url}</span>
                                <button
                                  type="button"
                                  aria-label="Remove link"
                                  onClick={() =>
                                    setFileUrls((prev) => prev.filter((_, i) => i !== idx))
                                  }
                                  className="text-ink-500 hover:text-danger-600"
                                >
                                  <Trash2 className="h-3.5 w-3.5" />
                                </button>
                              </li>
                            ))}
                          </ul>
                        )}
                      </div>

                      <FileDropzone
                        files={localFiles}
                        onChange={setLocalFiles}
                        helperText="Selected filenames are appended to your submission notes."
                      />

                      <div className="flex justify-end">
                        <Button type="submit" loading={submitMutation.isPending}>
                          Submit deliverable
                        </Button>
                      </div>
                    </form>
                  </Card>
                )}

                {latestDeliverable ? (
                  <EvaluationSection
                    key={latestDeliverable.id}
                    deliverableId={latestDeliverable.id}
                    viewerRole={viewerRole}
                    milestoneStatus={milestone.status}
                    onDecisionDone={() => {
                      void queryClient.invalidateQueries({ queryKey: ["milestone", milestoneId] });
                      void queryClient.invalidateQueries({ queryKey: ["milestones", projectId] });
                      void queryClient.invalidateQueries({ queryKey: ["deliverables", milestoneId] });
                    }}
                  />
                ) : (
                  !canSubmit && (
                    <EmptyState
                      title="Awaiting deliverable submission"
                      description="Once the freelancer submits work for this milestone, you can run AI evaluation and record your decision here."
                    />
                  )
                )}

                {/* Member 4 Payment Card */}
                <Card className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="text-base font-semibold text-ink-900">Milestone payment</h3>
                    <Link
                      to={`/projects/${projectId}/payments`}
                      className="text-xs font-semibold text-brand-600 hover:underline"
                    >
                      View payment ledger →
                    </Link>
                  </div>
                  <PayMilestoneCard
                    projectId={String(projectId)}
                    milestone={{
                      id: String(milestone.id),
                      title: milestone.title,
                      amount: String(milestone.amount),
                      status: milestone.status,
                    }}
                    viewerRole={viewerRole}
                    api={paymentApi}
                  />
                </Card>
              </div>
            </div>
          </div>
        );
      }}
    </ProjectLayout>
  );
}

