import type { Payment, PaymentApi, PaymentLedger } from "../../features/payments/PaymentApi";
import type {
  Agreement,
  AgreementContent,
  Deliverable,
  Evaluation,
  Milestone,
  Project,
  TokenResponse,
  User,
} from "../types";
import { createMockPaymentLedger, INITIAL_MOCK_DB, type MockDatabase } from "./mockData";

const STORAGE_KEY = "mm_mock_db_v1";

function loadDb(): MockDatabase {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw) as MockDatabase;
  } catch {
    // fallback to initial
  }
  return structuredClone(INITIAL_MOCK_DB);
}

function saveDb(db: MockDatabase): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(db));
  } catch {
    // ignore
  }
}

function nextId(db: MockDatabase): number {
  db.nextId += 1;
  return db.nextId;
}

export const mockApi = {
  reset(): void {
    saveDb(structuredClone(INITIAL_MOCK_DB));
  },

  async login(email: string): Promise<TokenResponse> {
    const db = loadDb();
    const user = db.users.find((u) => u.email.toLowerCase() === email.toLowerCase());
    if (!user) throw new Error("Invalid email or password.");
    db.currentUserId = user.id;
    saveDb(db);
    return { access_token: `mock-token-${user.id}`, token_type: "bearer" };
  },

  async register(data: {
    name: string;
    email: string;
    password: string;
    role: "client" | "freelancer";
  }): Promise<User> {
    const db = loadDb();
    if (db.users.some((u) => u.email.toLowerCase() === data.email.toLowerCase())) {
      throw new Error("An account with this email already exists.");
    }
    const user: User = {
      id: nextId(db),
      name: data.name,
      email: data.email.toLowerCase(),
      role: data.role,
      is_active: true,
    };
    db.users.push(user);
    saveDb(db);
    return user;
  },

  async me(): Promise<User> {
    const db = loadDb();
    const user = db.users.find((u) => u.id === db.currentUserId);
    if (!user) throw new Error("Not authenticated.");
    return user;
  },

  async listProjects(): Promise<Project[]> {
    const db = loadDb();
    const userId = db.currentUserId;
    return db.projects.filter((p) => p.client_id === userId || p.freelancer_id === userId);
  },

  async getProject(projectId: number): Promise<Project> {
    const db = loadDb();
    const project = db.projects.find((p) => p.id === projectId);
    if (!project) throw new Error("Project not found.");
    return project;
  },

  async createProject(data: {
    title: string;
    description: string;
    budget: string;
    currency: string;
    freelancer_id?: number | null;
  }): Promise<Project> {
    const db = loadDb();
    const now = new Date().toISOString();
    const project: Project = {
      id: nextId(db),
      title: data.title,
      description: data.description,
      budget: Number.parseFloat(data.budget).toFixed(2),
      currency: data.currency,
      status: "draft",
      client_id: db.currentUserId ?? 1,
      freelancer_id: data.freelancer_id ?? null,
      created_at: now,
      updated_at: now,
    };
    db.projects.unshift(project);
    saveDb(db);
    return project;
  },

  async assignFreelancer(projectId: number, freelancerId: number): Promise<Project> {
    const db = loadDb();
    const project = db.projects.find((p) => p.id === projectId);
    if (!project) throw new Error("Project not found.");
    project.freelancer_id = freelancerId;
    project.updated_at = new Date().toISOString();
    saveDb(db);
    return project;
  },

  async listAgreements(projectId: number): Promise<Agreement[]> {
    const db = loadDb();
    return db.agreements
      .filter((a) => a.project_id === projectId)
      .sort((a, b) => b.version - a.version);
  },

  async createAgreement(projectId: number, content: AgreementContent): Promise<Agreement> {
    const db = loadDb();
    const existing = db.agreements.filter((a) => a.project_id === projectId);
    const version = existing.reduce((max, a) => Math.max(max, a.version), 0) + 1;
    const agreement: Agreement = {
      id: nextId(db),
      project_id: projectId,
      version,
      content,
      status: "draft",
      client_approved_at: null,
      freelancer_approved_at: null,
    };
    db.agreements.push(agreement);
    saveDb(db);
    return agreement;
  },

  async approveAgreement(agreementId: number, approved: boolean): Promise<Agreement> {
    const db = loadDb();
    const agreement = db.agreements.find((a) => a.id === agreementId);
    if (!agreement) throw new Error("Agreement not found.");
    const project = db.projects.find((p) => p.id === agreement.project_id);
    if (!approved) {
      agreement.status = "rejected";
      saveDb(db);
      return agreement;
    }
    const now = new Date().toISOString();
    if (project && db.currentUserId === project.client_id) {
      agreement.client_approved_at = now;
    } else {
      agreement.freelancer_approved_at = now;
    }
    if (agreement.client_approved_at && agreement.freelancer_approved_at) {
      agreement.status = "approved";
      if (project) project.status = "active";
    }
    saveDb(db);
    return agreement;
  },

  async listMilestones(projectId: number): Promise<Milestone[]> {
    const db = loadDb();
    return db.milestones.filter((m) => m.project_id === projectId);
  },

  async getMilestone(milestoneId: number): Promise<Milestone> {
    const db = loadDb();
    const m = db.milestones.find((item) => item.id === milestoneId);
    if (!m) throw new Error("Milestone not found.");
    return m;
  },

  async createMilestone(
    projectId: number,
    data: {
      title: string;
      description: string;
      amount: string;
      due_date: string;
      acceptance_criteria: string[];
    },
  ): Promise<Milestone> {
    const db = loadDb();
    const agreement = db.agreements.find(
      (a) => a.project_id === projectId && a.status === "approved",
    );
    const milestone: Milestone = {
      id: nextId(db),
      project_id: projectId,
      agreement_id: agreement?.id ?? null,
      title: data.title,
      description: data.description,
      amount: Number.parseFloat(data.amount).toFixed(2),
      due_date: data.due_date,
      acceptance_criteria: data.acceptance_criteria,
      status: "pending",
    };
    db.milestones.push(milestone);
    saveDb(db);
    return milestone;
  },

  async listDeliverables(milestoneId: number): Promise<Deliverable[]> {
    const db = loadDb();
    return db.deliverables
      .filter((d) => d.milestone_id === milestoneId)
      .sort((a, b) => b.id - a.id);
  },

  async submitDeliverable(
    milestoneId: number,
    data: { description: string; file_urls: string[] },
  ): Promise<Deliverable> {
    const db = loadDb();
    const now = new Date().toISOString();
    const deliverable: Deliverable = {
      id: nextId(db),
      milestone_id: milestoneId,
      submitted_by_id: db.currentUserId ?? 2,
      description: data.description,
      file_urls: data.file_urls,
      status: "submitted",
      created_at: now,
      updated_at: now,
    };
    const milestone = db.milestones.find((m) => m.id === milestoneId);
    if (milestone) milestone.status = "submitted";
    db.deliverables.unshift(deliverable);
    saveDb(db);
    return deliverable;
  },

  async evaluateDeliverable(deliverableId: number): Promise<Evaluation> {
    const db = loadDb();
    const existing = db.evaluations.find((e) => e.deliverable_id === deliverableId);
    if (existing) return existing;
    const deliverable = db.deliverables.find((d) => d.id === deliverableId);
    const milestone = db.milestones.find((m) => m.id === deliverable?.milestone_id);
    const criteria = milestone?.acceptance_criteria ?? [];
    const evaluation: Evaluation = {
      id: nextId(db),
      deliverable_id: deliverableId,
      model_name: "gemini-3.8-flash (mock)",
      score: 92,
      recommendation: "approve",
      human_decision: null,
      findings: {
        summary: "Submission addresses the agreed acceptance criteria with verifiable notes.",
        criteria_results: criteria.map((criterion) => ({
          criterion,
          status: "met",
          evidence: deliverable?.description.slice(0, 120) ?? "Provided in submission.",
        })),
        missing_requirements: [],
      },
    };
    db.evaluations.push(evaluation);
    saveDb(db);
    return evaluation;
  },

  async submitEvaluationDecision(
    evaluationId: number,
    decision: "accepted" | "revision_requested",
  ): Promise<Evaluation> {
    const db = loadDb();
    const evaluation = db.evaluations.find((e) => e.id === evaluationId);
    if (!evaluation) throw new Error("Evaluation not found.");
    evaluation.human_decision = decision;
    const deliverable = db.deliverables.find((d) => d.id === evaluation.deliverable_id);
    const milestone = db.milestones.find((m) => m.id === deliverable?.milestone_id);
    if (deliverable) deliverable.status = decision;
    if (milestone) milestone.status = decision === "accepted" ? "approved" : "revision_requested";
    saveDb(db);
    return evaluation;
  },

  getEvaluationForDeliverable(deliverableId: number): Evaluation | null {
    const db = loadDb();
    return db.evaluations.find((e) => e.deliverable_id === deliverableId) ?? null;
  },
};

export function createMockPaymentApi(): PaymentApi {
  return {
    async createPayment(milestoneId: string): Promise<Payment> {
      const db = loadDb();
      const mid = Number(milestoneId);
      const milestone = db.milestones.find((m) => m.id === mid);
      if (!milestone) throw new Error("Milestone not found.");
      const id = nextId(db);
      const orderId = `MOCK-ORDER-${id}`;
      const payment: Payment = {
        id,
        milestone_id: mid,
        milestone_title: milestone.title,
        project_id: milestone.project_id,
        amount: milestone.amount,
        currency: "USD",
        status: "PENDING_APPROVAL",
        provider: "MOCK",
        paypal_order_id: orderId,
        paypal_capture_id: null,
        approve_url: `/payments/return?payment_id=${id}&token=${orderId}`,
        created_at: new Date().toISOString(),
        approved_at: null,
        captured_at: null,
        payee_mode: "demo_merchant",
        webhook_verified: false,
        events: [
          {
            event_type: "ORDER_CREATED",
            from_status: "CREATED",
            to_status: "PENDING_APPROVAL",
            source: "API",
            paypal_ref: orderId,
            created_at: new Date().toISOString(),
          },
        ],
      };
      db.payments.unshift(payment);
      saveDb(db);
      return payment;
    },
    async getPayment(paymentId: string): Promise<Payment> {
      const db = loadDb();
      const payment = db.payments.find((p) => p.id === Number(paymentId));
      if (!payment) throw new Error("Payment not found.");
      return payment;
    },
    async capturePayment(paymentId: string, orderId: string): Promise<Payment> {
      const db = loadDb();
      const payment = db.payments.find((p) => p.id === Number(paymentId));
      if (!payment) throw new Error("Payment not found.");
      payment.status = "COMPLETED";
      payment.paypal_order_id = orderId;
      payment.paypal_capture_id = `MOCK-CAP-${payment.id}`;
      payment.approved_at = new Date().toISOString();
      payment.captured_at = new Date().toISOString();
      payment.webhook_verified = true;
      payment.events = [
        ...(payment.events ?? []),
        {
          event_type: "CAPTURE_COMPLETED",
          from_status: "PENDING_APPROVAL",
          to_status: "COMPLETED",
          source: "API",
          paypal_ref: payment.paypal_capture_id,
          created_at: new Date().toISOString(),
        },
      ];
      const milestone = db.milestones.find((m) => m.id === payment.milestone_id);
      if (milestone) milestone.status = "paid";
      saveDb(db);
      return payment;
    },
    async cancelPayment(paymentId: string): Promise<Payment> {
      const db = loadDb();
      const payment = db.payments.find((p) => p.id === Number(paymentId));
      if (!payment) throw new Error("Payment not found.");
      payment.status = "CANCELLED";
      saveDb(db);
      return payment;
    },
    async syncPayment(paymentId: string): Promise<Payment> {
      const db = loadDb();
      const payment = db.payments.find((p) => p.id === Number(paymentId));
      if (!payment) throw new Error("Payment not found.");
      return payment;
    },
    async getProjectPayments(projectId: string): Promise<PaymentLedger> {
      const db = loadDb();
      return createMockPaymentLedger(db, Number(projectId));
    },
  };
}

