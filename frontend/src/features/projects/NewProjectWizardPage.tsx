import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, ArrowRight, CheckCircle2, Sparkles } from "lucide-react";
import { api } from "../../api/endpoints";
import type { AgreementContent, AgreementPlannedMilestone } from "../../api/types";
import {
  AiChip,
  Badge,
  Button,
  Card,
  DateInput,
  Input,
  MoneyInput,
  Textarea,
  useToast,
} from "../../components/ui";
import { centsToDecimalString, parseMoneyCents } from "../../lib/format";

const SAMPLE_BRIEF = {
  title: "Landing page and copy for Ember & Oak coffee subscription",
  description:
    "We are a small specialty coffee roaster launching a subscription. We need brand copy, a one-page responsive landing site with a signup form, and launch QA. Budget is $1,200, target launch in 3 weeks.",
  budget: "1200.00",
};

function addDaysIsoDate(days: number): string {
  const date = new Date(Date.now() + days * 24 * 60 * 60 * 1000);
  return date.toISOString().slice(0, 10);
}

function buildStarterMilestones(budget: string, targetDate: string): AgreementPlannedMilestone[] {
  const totalCents = Math.max(parseMoneyCents(budget), 300);
  const m1 = Math.round(totalCents * 0.25);
  const m2 = Math.round(totalCents * 0.5);
  const m3 = totalCents - m1 - m2;

  const endMs = targetDate ? new Date(targetDate).getTime() : Date.now() + 21 * 86400_000;
  const startMs = Date.now();
  const span = Math.max(endMs - startMs, 6 * 86400_000);

  const fmtDate = (ms: number) => new Date(ms).toISOString().slice(0, 10);

  return [
    {
      title: "Discovery, copy & architecture",
      description: "Initial messaging, structure, and technical plan aligned with the project brief.",
      amount: centsToDecimalString(m1),
      due_date: fmtDate(startMs + span * 0.33),
      acceptance_criteria: [
        "Deliverable covers core project brief requirements and structure",
        "All key copy or specification sections are clearly documented",
      ],
    },
    {
      title: "Core implementation",
      description: "Primary build covering the agreed deliverables and integrations.",
      amount: centsToDecimalString(m2),
      due_date: fmtDate(startMs + span * 0.72),
      acceptance_criteria: [
        "Core functional requirements implemented and verifiable",
        "Responsive layout and input validation verified",
      ],
    },
    {
      title: "QA & final handoff",
      description: "Final quality verification, bug fixes, and handoff documentation.",
      amount: centsToDecimalString(m3),
      due_date: fmtDate(startMs + span),
      acceptance_criteria: [
        "QA checklist completed with zero critical defects",
        "Final handoff notes and links provided",
      ],
    },
  ];
}

export function NewProjectWizardPage() {
  const navigate = useNavigate();
  const { pushToast } = useToast();

  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [budget, setBudget] = useState("1200.00");
  const [targetDate, setTargetDate] = useState(addDaysIsoDate(21));
  const [freelancerId, setFreelancerId] = useState("");
  const [clarifications, setClarifications] = useState({
    integrations: "",
    deliverablesFormat: "",
    revisionRounds: "Two revision rounds per milestone",
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const step1Valid =
    title.trim().length >= 3 &&
    description.trim().length >= 10 &&
    parseMoneyCents(budget) > 0;

  async function handleFinish(mode: "template" | "blank") {
    setError(null);
    setSubmitting(true);
    try {
      const parsedFreelancerId = freelancerId.trim()
        ? Number.parseInt(freelancerId.trim(), 10)
        : undefined;

      if (freelancerId.trim() && (!Number.isFinite(parsedFreelancerId) || (parsedFreelancerId ?? 0) <= 0)) {
        setError("Freelancer ID must be a positive number.");
        setSubmitting(false);
        return;
      }

      const project = await api.createProject({
        title: title.trim(),
        description: description.trim(),
        budget: Number.parseFloat(budget).toFixed(2),
        currency: "USD",
        freelancer_id: parsedFreelancerId ?? null,
      });

      const plannedMilestones =
        mode === "template" ? buildStarterMilestones(budget, targetDate) : [];

      const content: AgreementContent = {
        title: title.trim(),
        summary: description.trim(),
        scope_in: [
          description.trim(),
          ...(clarifications.integrations.trim()
            ? [`Integration: ${clarifications.integrations.trim()}`]
            : []),
          ...(clarifications.deliverablesFormat.trim()
            ? [`Deliverables format: ${clarifications.deliverablesFormat.trim()}`]
            : []),
        ],
        scope_out: ["Out-of-scope additions require a separate agreement revision."],
        assumptions: ["Client supplies required brand assets and timely milestone feedback."],
        payment_terms:
          "Each milestone is paid via PayPal only after the client explicitly accepts the milestone deliverable.",
        revision_policy: clarifications.revisionRounds.trim() || "Two revision rounds per milestone.",
        total_amount: Number.parseFloat(budget).toFixed(2),
        origin: "TEMPLATE",
        planned_milestones: plannedMilestones,
      };

      await api.createAgreement(project.id, content);
      pushToast({
        tone: "success",
        title: "Project & draft agreement created",
        description: "Review and refine your agreement before approving.",
      });
      navigate(`/projects/${project.id}/agreement`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create project.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-ink-900">Create a new project</h1>
          <p className="mt-0.5 text-sm text-ink-600">
            Describe your goals, clarify expectations, and generate an editable milestone agreement.
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs font-medium">
          {[
            { n: 1, label: "1. Describe" },
            { n: 2, label: "2. Clarify" },
            { n: 3, label: "3. Draft" },
          ].map((s) => (
            <Badge key={s.n} tone={step === s.n ? "brand" : step > s.n ? "success" : "gray"}>
              {s.label}
            </Badge>
          ))}
        </div>
      </div>

      {step === 1 && (
        <Card className="space-y-5">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-ink-900">Step 1: Describe your project</h2>
            <Button
              size="sm"
              variant="secondary"
              onClick={() => {
                setTitle(SAMPLE_BRIEF.title);
                setDescription(SAMPLE_BRIEF.description);
                setBudget(SAMPLE_BRIEF.budget);
              }}
            >
              Use sample brief
            </Button>
          </div>

          <Input
            id="proj-title"
            label="Project title"
            required
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g., Landing page and copy for Ember & Oak coffee"
          />

          <Textarea
            id="proj-brief"
            label="Project brief"
            required
            rows={5}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Describe what needs to be built, key deliverables, integrations, and timeline..."
            hint={`${description.trim().length} characters (minimum 10 required)`}
          />

          <div className="grid gap-4 sm:grid-cols-2">
            <MoneyInput
              id="proj-budget"
              label="Total budget"
              required
              value={budget}
              onChange={setBudget}
            />
            <DateInput
              id="proj-target-date"
              label="Target completion date"
              value={targetDate}
              onChange={(e) => setTargetDate(e.target.value)}
            />
          </div>

          <Input
            id="proj-freelancer-id"
            label="Freelancer user ID (optional)"
            type="number"
            min={1}
            value={freelancerId}
            onChange={(e) => setFreelancerId(e.target.value)}
            hint="If you already know the freelancer's user ID, enter it now or assign them later."
          />

          <div className="flex justify-end pt-2">
            <Button
              disabled={!step1Valid}
              onClick={() => setStep(2)}
              icon={<ArrowRight className="h-4 w-4" />}
            >
              Continue to clarify
            </Button>
          </div>
        </Card>
      )}

      {step === 2 && (
        <Card className="space-y-5">
          <div className="flex items-center justify-between gap-2">
            <div>
              <h2 className="text-lg font-semibold text-ink-900">Step 2: Clarify key scope details</h2>
              <p className="mt-0.5 text-sm text-ink-600">
                Answering these questions makes milestone acceptance criteria unambiguous.
              </p>
            </div>
            <AiChip label="Scope checklist" />
          </div>

          <Textarea
            id="clarify-integrations"
            label="Which external tools, APIs, or services should be connected?"
            rows={2}
            value={clarifications.integrations}
            onChange={(e) =>
              setClarifications((prev) => ({ ...prev, integrations: e.target.value }))
            }
            placeholder="e.g., Mailchimp signup API, Stripe checkout, GitHub repo"
          />

          <Textarea
            id="clarify-format"
            label="What deliverable formats or links do you expect for review?"
            rows={2}
            value={clarifications.deliverablesFormat}
            onChange={(e) =>
              setClarifications((prev) => ({ ...prev, deliverablesFormat: e.target.value }))
            }
            placeholder="e.g., Deployed preview URL, Markdown copy doc, QA test checklist"
          />

          <Input
            id="clarify-revisions"
            label="Revision policy"
            value={clarifications.revisionRounds}
            onChange={(e) =>
              setClarifications((prev) => ({ ...prev, revisionRounds: e.target.value }))
            }
          />

          <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
            <Button
              variant="secondary"
              onClick={() => setStep(1)}
              icon={<ArrowLeft className="h-4 w-4" />}
            >
              Back
            </Button>
            <div className="flex gap-2">
              <Button variant="ghost" onClick={() => setStep(3)}>
                Skip questions
              </Button>
              <Button onClick={() => setStep(3)} icon={<ArrowRight className="h-4 w-4" />}>
                Review draft options
              </Button>
            </div>
          </div>
        </Card>
      )}

      {step === 3 && (
        <Card className="space-y-5">
          <div className="space-y-1">
            <h2 className="text-lg font-semibold text-ink-900">
              Step 3: Create project &amp; initial agreement
            </h2>
            <p className="text-sm text-ink-600">
              We will persist your project and generate an editable 3-milestone agreement draft
              (25% / 50% / 25% split) ready for review and approval.
            </p>
          </div>

          <div className="rounded-xl border border-ink-300/70 bg-canvas p-4 text-sm">
            <p className="font-semibold text-ink-900">{title}</p>
            <p className="mt-1 text-xs text-ink-600">{description}</p>
            <div className="mt-3 flex flex-wrap gap-4 text-xs text-ink-700">
              <span>
                Total budget: <strong>${Number.parseFloat(budget || "0").toFixed(2)} USD</strong>
              </span>
              <span>
                Target date: <strong>{targetDate || "Flexible"}</strong>
              </span>
              <span>
                Milestones: <strong>3 starter milestones</strong>
              </span>
            </div>
          </div>

          {error && (
            <p
              role="alert"
              className="rounded-lg border border-red-200 bg-danger-50 px-3 py-2 text-xs font-medium text-danger-700"
            >
              {error}
            </p>
          )}

          <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
            <Button
              variant="secondary"
              onClick={() => setStep(2)}
              disabled={submitting}
              icon={<ArrowLeft className="h-4 w-4" />}
            >
              Back
            </Button>
            <div className="flex flex-wrap gap-2">
              <Button
                variant="secondary"
                disabled={submitting}
                onClick={() => void handleFinish("blank")}
              >
                Create with blank agreement
              </Button>
              <Button
                loading={submitting}
                onClick={() => void handleFinish("template")}
                icon={<Sparkles className="h-4 w-4" />}
              >
                Create project &amp; draft agreement
              </Button>
            </div>
          </div>

          <p className="flex items-center gap-1.5 text-xs text-ink-500">
            <CheckCircle2 className="h-3.5 w-3.5 text-success-600" />
            Nothing is final until both client and freelancer approve the agreement.
          </p>
        </Card>
      )}
    </div>
  );
}

