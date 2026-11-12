import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Plus, UserCheck } from "lucide-react";
import { api } from "../../api/endpoints";
import { getPaymentApi } from "../../api/paymentsAdapter";
import { ProjectLayout } from "../../components/layout/ProjectLayout";
import {
  Button,
  Card,
  DateInput,
  EmptyState,
  Input,
  MilestoneStepper,
  Modal,
  MoneyInput,
  MoneyText,
  StatusBadge,
  Textarea,
  useToast,
} from "../../components/ui";
import { parseMoneyCents, toIsoUtcEndOfDay } from "../../lib/format";

export function ProjectOverviewPage({ projectId }: { projectId: number }) {
  const queryClient = useQueryClient();
  const { pushToast } = useToast();
  const paymentApi = getPaymentApi();

  const [freelancerInput, setFreelancerInput] = useState("");
  const [milestoneModalOpen, setMilestoneModalOpen] = useState(false);
  const [msTitle, setMsTitle] = useState("");
  const [msDescription, setMsDescription] = useState("");
  const [msAmount, setMsAmount] = useState("");
  const [msDueDate, setMsDueDate] = useState(
    new Date(Date.now() + 7 * 86400_000).toISOString().slice(0, 10),
  );
  const [msCriteriaText, setMsCriteriaText] = useState("");

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

  const assignMutation = useMutation({
    mutationFn: (freelancerId: number) => api.assignFreelancer(projectId, freelancerId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["project", projectId] });
      pushToast({ tone: "success", title: "Freelancer assigned to project" });
      setFreelancerInput("");
    },
    onError: (err) => {
      pushToast({
        tone: "error",
        title: "Could not assign freelancer",
        description: err instanceof Error ? err.message : undefined,
      });
    },
  });

  const createMilestoneMutation = useMutation({
    mutationFn: () => {
      const criteria = msCriteriaText
        .split("\n")
        .map((line) => line.trim())
        .filter(Boolean);
      return api.createMilestone(projectId, {
        title: msTitle.trim(),
        description: msDescription.trim(),
        amount: Number.parseFloat(msAmount).toFixed(2),
        due_date: toIsoUtcEndOfDay(msDueDate),
        acceptance_criteria: criteria.length > 0 ? criteria : ["Deliverable meets agreed scope"],
      });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["milestones", projectId] });
      pushToast({ tone: "success", title: "Milestone added" });
      setMilestoneModalOpen(false);
      setMsTitle("");
      setMsDescription("");
      setMsAmount("");
      setMsCriteriaText("");
    },
    onError: (err) => {
      pushToast({
        tone: "error",
        title: "Could not create milestone",
        description: err instanceof Error ? err.message : undefined,
      });
    },
  });

  return (
    <ProjectLayout projectId={projectId} activeTab="overview">
      {({ project, viewerRole }) => {
        const latestAgreement = agreements[0];
        const allocatedCents = milestones.reduce(
          (acc, m) => acc + parseMoneyCents(m.amount),
          0,
        );
        const budgetCents = parseMoneyCents(project.budget);
        const remainingAllocCents = Math.max(budgetCents - allocatedCents, 0);

        const isActive = project.status.toLowerCase() === "active";

        let nextAction = {
          title: "View project agreement",
          description: "Review project scope, milestones, and approval history.",
          to: `/projects/${projectId}/agreement`,
          cta: "Open agreement",
        };

        if (!project.freelancer_id && viewerRole === "CLIENT") {
          nextAction = {
            title: "Assign a freelancer",
            description:
              "Enter your freelancer's user ID below so they can review and approve the agreement.",
            to: `/projects/${projectId}/agreement`,
            cta: "Go to agreement",
          };
        } else if (!latestAgreement || latestAgreement.status.toLowerCase() === "draft") {
          nextAction = {
            title: "Approve project agreement",
            description:
              "Both client and freelancer must approve the same agreement version before milestones become active.",
            to: `/projects/${projectId}/agreement`,
            cta: "Review & approve agreement",
          };
        } else if (isActive && milestones.length === 0 && viewerRole === "CLIENT") {
          nextAction = {
            title: "Add project milestones",
            description:
              "Agreement is approved. Create the executable milestones or import them from your agreement plan.",
            to: `/projects/${projectId}/agreement`,
            cta: "Manage milestones",
          };
        } else {
          const pendingPay = milestones.find((m) => m.status.toLowerCase() === "approved");
          const submitted = milestones.find((m) => m.status.toLowerCase() === "submitted");
          const openWork = milestones.find((m) =>
            ["pending", "revision_requested"].includes(m.status.toLowerCase()),
          );

          if (viewerRole === "CLIENT" && pendingPay) {
            nextAction = {
              title: `Pay accepted milestone: ${pendingPay.title}`,
              description: "You accepted this deliverable. Authorize payment via PayPal.",
              to: `/projects/${projectId}/milestones/${pendingPay.id}`,
              cta: "Pay with PayPal",
            };
          } else if (viewerRole === "CLIENT" && submitted) {
            nextAction = {
              title: `Evaluate deliverable: ${submitted.title}`,
              description: "The freelancer submitted work. Run AI evaluation and record your decision.",
              to: `/projects/${projectId}/milestones/${submitted.id}`,
              cta: "Review submission",
            };
          } else if (viewerRole === "FREELANCER" && openWork) {
            nextAction = {
              title: `Submit deliverable: ${openWork.title}`,
              description: "Share your work description and deliverable links for client review.",
              to: `/projects/${projectId}/milestones/${openWork.id}`,
              cta: "Submit deliverable",
            };
          }
        }

        function handleAssign(e: FormEvent) {
          e.preventDefault();
          const parsed = Number.parseInt(freelancerInput.trim(), 10);
          if (!Number.isFinite(parsed) || parsed <= 0) return;
          assignMutation.mutate(parsed);
        }

        return (
          <div className="space-y-6">
            {/* Summary strip */}
            <div className="grid gap-4 md:grid-cols-3">
              <Card>
                <p className="text-xs font-medium text-ink-500">Paid / Total budget</p>
                <p className="mt-1 text-lg font-bold text-ink-900">
                  <MoneyText value={ledger?.totals.paid ?? "0.00"} />{" "}
                  <span className="text-sm font-normal text-ink-500">
                    of <MoneyText value={project.budget} />
                  </span>
                </p>
              </Card>
              <Card>
                <p className="text-xs font-medium text-ink-500">Agreement status</p>
                <div className="mt-1.5 flex items-center gap-2">
                  {latestAgreement ? (
                    <>
                      <StatusBadge status={latestAgreement.status} context="agreement" />
                      <span className="text-xs text-ink-600">v{latestAgreement.version}</span>
                    </>
                  ) : (
                    <span className="text-sm text-ink-600">No agreement created yet</span>
                  )}
                </div>
              </Card>
              <Card>
                <p className="text-xs font-medium text-ink-500">Counterparty</p>
                <p className="mt-1 text-sm font-semibold text-ink-900">
                  {viewerRole === "CLIENT"
                    ? project.freelancer_id
                      ? `Freelancer User #${project.freelancer_id}`
                      : "Not assigned yet"
                    : `Client User #${project.client_id}`}
                </p>
              </Card>
            </div>

            {/* Next action card */}
            <Card className="flex flex-wrap items-center justify-between gap-4 border-brand-100 bg-brand-50/40">
              <div className="space-y-1">
                <p className="text-xs font-semibold uppercase tracking-wide text-brand-700">
                  Recommended next step
                </p>
                <h2 className="text-base font-semibold text-ink-900">{nextAction.title}</h2>
                <p className="text-sm text-ink-600">{nextAction.description}</p>
              </div>
              <Link to={nextAction.to}>
                <Button icon={<ArrowRight className="h-4 w-4" />}>{nextAction.cta}</Button>
              </Link>
            </Card>

            {/* Freelancer assignment card for draft projects */}
            {viewerRole === "CLIENT" && !project.freelancer_id && project.status === "draft" && (
              <Card>
                <div className="flex items-start gap-3">
                  <UserCheck className="mt-1 h-5 w-5 text-brand-600" aria-hidden="true" />
                  <div className="flex-1 space-y-3">
                    <div>
                      <h2 className="text-base font-semibold text-ink-900">
                        Assign a freelancer to this project
                      </h2>
                      <p className="text-sm text-ink-600">
                        Ask your freelancer for their User ID (shown on their Profile page) and
                        assign them so they can review and approve the agreement.
                      </p>
                    </div>
                    <form onSubmit={handleAssign} className="flex flex-wrap items-end gap-3">
                      <div className="w-48">
                        <Input
                          id="assign-freelancer-id"
                          label="Freelancer User ID"
                          type="number"
                          min={1}
                          required
                          value={freelancerInput}
                          onChange={(e) => setFreelancerInput(e.target.value)}
                          placeholder="e.g., 2"
                        />
                      </div>
                      <Button type="submit" loading={assignMutation.isPending}>
                        Assign freelancer
                      </Button>
                    </form>
                  </div>
                </div>
              </Card>
            )}

            {/* Milestones stepper */}
            <div id="milestones" className="space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h2 className="text-lg font-semibold text-ink-900">Milestones</h2>
                  <p className="text-xs text-ink-600">
                    Allocated: <MoneyText value={(allocatedCents / 100).toFixed(2)} /> of{" "}
                    <MoneyText value={project.budget} />
                  </p>
                </div>
                {viewerRole === "CLIENT" && isActive && remainingAllocCents > 0 && (
                  <Button
                    size="sm"
                    variant="secondary"
                    icon={<Plus className="h-4 w-4" />}
                    onClick={() => {
                      setMsAmount((remainingAllocCents / 100).toFixed(2));
                      setMilestoneModalOpen(true);
                    }}
                  >
                    Add milestone
                  </Button>
                )}
              </div>

              {milestones.length === 0 ? (
                <EmptyState
                  title="No active milestones yet"
                  description={
                    isActive
                      ? "Add milestones from the button above or sync them from your approved agreement."
                      : "Milestones are created once both client and freelancer approve the agreement."
                  }
                  action={
                    !isActive ? (
                      <Link to={`/projects/${projectId}/agreement`}>
                        <Button variant="secondary">Open agreement</Button>
                      </Link>
                    ) : undefined
                  }
                />
              ) : (
                <MilestoneStepper
                  items={milestones.map((m) => ({
                    id: m.id,
                    title: m.title,
                    amount: m.amount,
                    dueDate: m.due_date,
                    status: m.status,
                    to: `/projects/${projectId}/milestones/${m.id}`,
                  }))}
                />
              )}
            </div>

            <Modal
              open={milestoneModalOpen}
              onClose={() => setMilestoneModalOpen(false)}
              title="Add executable milestone"
              description={`Remaining unallocated project budget: $${(remainingAllocCents / 100).toFixed(2)} USD`}
              footer={
                <>
                  <Button variant="secondary" onClick={() => setMilestoneModalOpen(false)}>
                    Cancel
                  </Button>
                  <Button
                    loading={createMilestoneMutation.isPending}
                    disabled={
                      msTitle.trim().length < 3 ||
                      msDescription.trim().length < 5 ||
                      parseMoneyCents(msAmount) <= 0
                    }
                    onClick={() => createMilestoneMutation.mutate()}
                  >
                    Create milestone
                  </Button>
                </>
              }
            >
              <div className="space-y-3">
                <Input
                  id="new-ms-title"
                  label="Milestone title"
                  required
                  value={msTitle}
                  onChange={(e) => setMsTitle(e.target.value)}
                />
                <Textarea
                  id="new-ms-desc"
                  label="Description"
                  required
                  rows={3}
                  value={msDescription}
                  onChange={(e) => setMsDescription(e.target.value)}
                />
                <div className="grid gap-3 sm:grid-cols-2">
                  <MoneyInput
                    id="new-ms-amount"
                    label="Amount"
                    required
                    value={msAmount}
                    onChange={setMsAmount}
                  />
                  <DateInput
                    id="new-ms-date"
                    label="Due date"
                    required
                    value={msDueDate}
                    onChange={(e) => setMsDueDate(e.target.value)}
                  />
                </div>
                <Textarea
                  id="new-ms-criteria"
                  label="Acceptance criteria (one per line)"
                  rows={3}
                  value={msCriteriaText}
                  onChange={(e) => setMsCriteriaText(e.target.value)}
                  placeholder={"Responsive on 375px and 1280px\nSignup form validates email"}
                />
              </div>
            </Modal>
          </div>
        );
      }}
    </ProjectLayout>
  );
}

