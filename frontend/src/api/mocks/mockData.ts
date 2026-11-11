import type { Payment, PaymentLedger } from "../../features/payments/PaymentApi";
import type {
  Agreement,
  Deliverable,
  Evaluation,
  Milestone,
  Project,
  User,
} from "../types";

export interface MockDatabase {
  users: User[];
  currentUserId: number | null;
  projects: Project[];
  agreements: Agreement[];
  milestones: Milestone[];
  deliverables: Deliverable[];
  evaluations: Evaluation[];
  payments: Payment[];
  nextId: number;
}

export const INITIAL_MOCK_DB: MockDatabase = {
  nextId: 100,
  currentUserId: 1,
  users: [
    {
      id: 1,
      name: "Maya Rao",
      email: "client@demo.milestonemate.test",
      role: "client",
      is_active: true,
    },
    {
      id: 2,
      name: "Dev Patel",
      email: "freelancer@demo.milestonemate.test",
      role: "freelancer",
      is_active: true,
    },
  ],
  projects: [
    {
      id: 1,
      title: "Ember & Oak Coffee Subscription Landing Page",
      description:
        "We are a small specialty coffee roaster launching a subscription. We need brand copy, a responsive one-page landing site with signup integration, and launch QA.",
      budget: "1200.00",
      currency: "USD",
      status: "active",
      client_id: 1,
      freelancer_id: 2,
      created_at: "2026-11-02T08:00:00Z",
      updated_at: "2026-11-05T10:00:00Z",
    },
  ],
  agreements: [
    {
      id: 1,
      project_id: 1,
      version: 1,
      status: "approved",
      client_approved_at: "2026-11-03T09:15:00Z",
      freelancer_approved_at: "2026-11-03T10:02:11Z",
      content: {
        title: "Ember & Oak Launch Package",
        summary:
          "Brand voice guide, conversion-focused landing copy, responsive site build, and launch QA.",
        scope_in: [
          "Brand voice guide & hero copy",
          "One-page responsive React/HTML landing site",
          "Mailchimp newsletter signup form",
          "Cross-browser launch QA report",
        ],
        scope_out: ["Logo design", "Paid social ad creatives"],
        assumptions: ["Client supplies product photography and Mailchimp list ID"],
        payment_terms:
          "Each milestone is paid via PayPal after the client explicitly reviews and accepts the deliverable.",
        revision_policy: "Up to two revision rounds per milestone.",
        total_amount: "1200.00",
        origin: "AI",
      },
    },
  ],
  milestones: [
    {
      id: 1,
      project_id: 1,
      agreement_id: 1,
      title: "Brand copy & sitemap",
      description: "Hero messaging, product story, subscription FAQ, and page wireframe outline.",
      amount: "300.00",
      due_date: "2026-11-10T23:59:59Z",
      acceptance_criteria: [
        "Copy includes hero headline, subhead, and primary CTA text",
        "Subscription tiers clearly state roast cadence and pricing",
        "Sitemap covers Hero, Roasts, How It Works, FAQ, and Footer",
      ],
      status: "paid",
    },
    {
      id: 2,
      project_id: 1,
      agreement_id: 1,
      title: "Landing page build & signup integration",
      description: "Responsive landing page implementing the approved copy and signup form.",
      amount: "600.00",
      due_date: "2026-11-17T23:59:59Z",
      acceptance_criteria: [
        "Responsive layout verified at 375px and 1280px",
        "Signup form validates email and confirms subscription state",
        "Lighthouse accessibility score >= 90",
      ],
      status: "submitted",
    },
    {
      id: 3,
      project_id: 1,
      agreement_id: 1,
      title: "Launch QA & handoff",
      description: "Final browser matrix check, metadata tags, and deployment handoff notes.",
      amount: "300.00",
      due_date: "2026-11-23T23:59:59Z",
      acceptance_criteria: [
        "QA checklist covers Chrome, Safari, and mobile viewport",
        "OpenGraph metadata and favicon verified",
      ],
      status: "pending",
    },
  ],
  deliverables: [
    {
      id: 1,
      milestone_id: 1,
      submitted_by_id: 2,
      description:
        "Completed copy.md with hero headline ('Roasted to order, delivered to your door'), pricing table, and 5-section sitemap.",
      file_urls: ["https://example.com/ember-oak-copy.md"],
      status: "accepted",
      created_at: "2026-11-04T14:20:00Z",
      updated_at: "2026-11-04T16:10:00Z",
    },
    {
      id: 2,
      milestone_id: 2,
      submitted_by_id: 2,
      description:
        "Built responsive landing page with mobile breakpoint at 375px, desktop grid at 1280px, email validation, and aria-live feedback.",
      file_urls: ["https://example.com/ember-oak-preview"],
      status: "submitted",
      created_at: "2026-11-11T10:30:00Z",
      updated_at: "2026-11-11T10:30:00Z",
    },
  ],
  evaluations: [
    {
      id: 1,
      deliverable_id: 1,
      model_name: "gemini-3.8-flash (mock)",
      score: 96,
      recommendation: "approve",
      human_decision: "accepted",
      findings: {
        summary: "All 3 acceptance criteria are explicitly addressed in the submitted copy.",
        criteria_results: [
          {
            criterion: "Copy includes hero headline, subhead, and primary CTA text",
            status: "met",
            evidence: "Hero headline 'Roasted to order, delivered to your door' and CTA provided.",
          },
          {
            criterion: "Subscription tiers clearly state roast cadence and pricing",
            status: "met",
            evidence: "Pricing table included for bi-weekly and monthly tiers.",
          },
          {
            criterion: "Sitemap covers Hero, Roasts, How It Works, FAQ, and Footer",
            status: "met",
            evidence: "5-section sitemap explicitly listed in submission.",
          },
        ],
        missing_requirements: [],
      },
    },
  ],
  payments: [
    {
      id: 1,
      milestone_id: 1,
      milestone_title: "Brand copy & sitemap",
      project_id: 1,
      amount: "300.00",
      currency: "USD",
      status: "COMPLETED",
      provider: "MOCK",
      paypal_order_id: "MOCK-ORDER-901",
      paypal_capture_id: "MOCK-CAP-901",
      approve_url: null,
      created_at: "2026-11-04T16:15:00Z",
      approved_at: "2026-11-04T16:16:00Z",
      captured_at: "2026-11-04T16:16:30Z",
      payee_mode: "demo_merchant",
      webhook_verified: true,
      events: [
        {
          event_type: "ORDER_CREATED",
          from_status: "CREATED",
          to_status: "PENDING_APPROVAL",
          source: "API",
          paypal_ref: "MOCK-ORDER-901",
          created_at: "2026-11-04T16:15:05Z",
        },
        {
          event_type: "CAPTURE_COMPLETED",
          from_status: "APPROVED",
          to_status: "COMPLETED",
          source: "API",
          paypal_ref: "MOCK-CAP-901",
          created_at: "2026-11-04T16:16:30Z",
        },
      ],
    },
  ],
};

export function createMockPaymentLedger(db: MockDatabase, projectId: number): PaymentLedger {
  const project = db.projects.find((p) => p.id === projectId);
  const items = db.payments.filter((p) => p.project_id === projectId);
  const paid = items
    .filter((p) => p.status === "COMPLETED")
    .reduce((acc, p) => acc + Number.parseFloat(p.amount), 0);
  const pending = items
    .filter((p) => ["CREATED", "PENDING_APPROVAL", "APPROVED", "CAPTURE_PENDING"].includes(p.status))
    .reduce((acc, p) => acc + Number.parseFloat(p.amount), 0);
  const budget = project ? Number.parseFloat(project.budget) : 0;
  const remaining = Math.max(budget - paid - pending, 0);

  return {
    items,
    totals: {
      paid: paid.toFixed(2),
      pending: pending.toFixed(2),
      remaining: remaining.toFixed(2),
    },
  };
}
