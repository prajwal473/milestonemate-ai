import { Link } from "react-router-dom";
import { ArrowRight, CheckCircle2, CreditCard, FileCheck2, Sparkles } from "lucide-react";
import { AiChip, Button, Card } from "../../components/ui";
import { useAuth } from "../auth/useAuth";

export function LandingPage() {
  const { user } = useAuth();

  return (
    <div className="space-y-12 py-4">
      <section className="rounded-2xl border border-ink-300/70 bg-surface p-6 shadow-sm sm:p-10">
        <div className="max-w-3xl space-y-5">
          <AiChip label="PayPal AI Hackathon 2026" />
          <h1 className="text-3xl font-bold tracking-tight text-ink-900 sm:text-4xl">
            From Project Agreement to Milestone Payment.
          </h1>
          <p className="text-base leading-relaxed text-ink-600 sm:text-lg">
            MilestoneMate AI turns plain-language briefs into clear, dual-approved milestone
            agreements, runs advisory AI deliverable evaluations against agreed acceptance criteria,
            and coordinates explicit PayPal milestone payments after your approval.
          </p>
          <div className="flex flex-wrap items-center gap-3 pt-1">
            <Link to={user ? "/dashboard" : "/register"}>
              <Button size="lg" icon={<ArrowRight className="h-4 w-4" />}>
                {user ? "Go to dashboard" : "Start a project"}
              </Button>
            </Link>
            {!user && (
              <Link to="/login">
                <Button variant="secondary" size="lg">
                  Sign in
                </Button>
              </Link>
            )}
          </div>
        </div>

        <div className="mt-10 grid gap-4 md:grid-cols-3">
          <div className="rounded-xl border border-ink-300/60 bg-canvas p-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-brand-700">
              <FileCheck2 className="h-4 w-4" />
              1. Describe &amp; Agree
            </div>
            <p className="mt-1.5 text-sm text-ink-600">
              Define scope, payment terms, and testable milestone criteria that both client and
              freelancer approve before work begins.
            </p>
          </div>
          <div className="rounded-xl border border-ink-300/60 bg-canvas p-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-ai-700">
              <Sparkles className="h-4 w-4" />
              2. Deliver &amp; Evaluate
            </div>
            <p className="mt-1.5 text-sm text-ink-600">
              Freelancers submit milestone deliverables; Gemini provides an evidence-backed
              evaluation report. You always make the final call.
            </p>
          </div>
          <div className="rounded-xl border border-ink-300/60 bg-canvas p-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-success-700">
              <CreditCard className="h-4 w-4" />
              3. Approve &amp; Pay via PayPal
            </div>
            <p className="mt-1.5 text-sm text-ink-600">
              Once you accept a milestone, pay via PayPal Sandbox Orders with server-side capture
              and an auditable payment ledger.
            </p>
          </div>
        </div>
      </section>

      <section className="grid gap-6 md:grid-cols-2">
        <Card>
          <h2 className="text-lg font-semibold text-ink-900">How AI helps without taking control</h2>
          <ul className="mt-3 space-y-2.5 text-sm text-ink-600">
            <li className="flex items-start gap-2">
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-ai-600" />
              <span>Structures project scopes and testable acceptance criteria up front.</span>
            </li>
            <li className="flex items-start gap-2">
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-ai-600" />
              <span>Evaluates deliverables against every agreed criterion with evidence notes.</span>
            </li>
            <li className="flex items-start gap-2">
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-ai-600" />
              <span>Advisory only — the AI never approves deliverables or captures payments.</span>
            </li>
          </ul>
        </Card>

        <Card>
          <h2 className="text-lg font-semibold text-ink-900">Transparent PayPal payment coordination</h2>
          <ul className="mt-3 space-y-2.5 text-sm text-ink-600">
            <li className="flex items-start gap-2">
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-success-600" />
              <span>Paid via PayPal only after the client explicitly accepts the milestone.</span>
            </li>
            <li className="flex items-start gap-2">
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-success-600" />
              <span>Idempotent order creation, verified capture, and full event audit trail.</span>
            </li>
            <li className="flex items-start gap-2">
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-success-600" />
              <span>Not an escrow service — runs against PayPal Sandbox / mock mode for demo.</span>
            </li>
          </ul>
        </Card>
      </section>
    </div>
  );
}

