import { env } from "../lib/env";
import { apiRequest } from "./client";
import { mockApi } from "./mocks/mockApi";
import type {
  Agreement,
  AgreementContent,
  Deliverable,
  Evaluation,
  HealthStatus,
  Milestone,
  Project,
  TokenResponse,
  User,
  UserRole,
} from "./types";

const EVAL_CACHE_PREFIX = "mm_eval_cache_";

function cacheEvaluation(evaluation: Evaluation): void {
  try {
    window.localStorage.setItem(
      `${EVAL_CACHE_PREFIX}${evaluation.deliverable_id}`,
      JSON.stringify(evaluation),
    );
  } catch {
    // ignore
  }
}

export function getCachedEvaluation(deliverableId: number): Evaluation | null {
  if (env.useMocks) {
    return mockApi.getEvaluationForDeliverable(deliverableId);
  }
  try {
    const raw = window.localStorage.getItem(`${EVAL_CACHE_PREFIX}${deliverableId}`);
    return raw ? (JSON.parse(raw) as Evaluation) : null;
  } catch {
    return null;
  }
}

export const api = {
  async health(): Promise<HealthStatus> {
    if (env.useMocks) {
      return {
        status: "ok",
        service: "MilestoneMate AI (Mock)",
        database: "mock",
        timestamp: new Date().toISOString(),
      };
    }
    return apiRequest<HealthStatus>("/api/health", { skipAuthRedirect: true });
  },

  async login(email: string, password: string): Promise<TokenResponse> {
    if (env.useMocks) return mockApi.login(email);
    return apiRequest<TokenResponse>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
      skipAuthRedirect: true,
    });
  },

  async register(payload: {
    name: string;
    email: string;
    password: string;
    role: UserRole;
  }): Promise<User> {
    if (env.useMocks) return mockApi.register(payload);
    return apiRequest<User>("/api/users/register", {
      method: "POST",
      body: JSON.stringify(payload),
      skipAuthRedirect: true,
    });
  },

  async me(): Promise<User> {
    if (env.useMocks) return mockApi.me();
    return apiRequest<User>("/api/users/me");
  },

  async listProjects(): Promise<Project[]> {
    if (env.useMocks) return mockApi.listProjects();
    return apiRequest<Project[]>("/api/projects");
  },

  async getProject(projectId: number): Promise<Project> {
    if (env.useMocks) return mockApi.getProject(projectId);
    return apiRequest<Project>(`/api/projects/${projectId}`);
  },

  async createProject(payload: {
    title: string;
    description: string;
    budget: string;
    currency: string;
    freelancer_id?: number | null;
  }): Promise<Project> {
    if (env.useMocks) return mockApi.createProject(payload);
    return apiRequest<Project>("/api/projects", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async updateProject(
    projectId: number,
    payload: { title?: string; description?: string; budget?: string; currency?: string },
  ): Promise<Project> {
    return apiRequest<Project>(`/api/projects/${projectId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },

  async assignFreelancer(projectId: number, freelancerId: number): Promise<Project> {
    if (env.useMocks) return mockApi.assignFreelancer(projectId, freelancerId);
    return apiRequest<Project>(`/api/projects/${projectId}/assign-freelancer`, {
      method: "POST",
      body: JSON.stringify({ freelancer_id: freelancerId }),
    });
  },

  async listAgreements(projectId: number): Promise<Agreement[]> {
    if (env.useMocks) return mockApi.listAgreements(projectId);
    return apiRequest<Agreement[]>(`/api/agreements/projects/${projectId}`);
  },

  async createAgreement(projectId: number, content: AgreementContent): Promise<Agreement> {
    if (env.useMocks) return mockApi.createAgreement(projectId, content);
    return apiRequest<Agreement>(`/api/agreements/projects/${projectId}`, {
      method: "POST",
      body: JSON.stringify({ content }),
    });
  },

  async approveAgreement(agreementId: number, approved = true): Promise<Agreement> {
    if (env.useMocks) return mockApi.approveAgreement(agreementId, approved);
    return apiRequest<Agreement>(`/api/agreements/${agreementId}/approve`, {
      method: "POST",
      body: JSON.stringify({ approved }),
    });
  },

  async listMilestones(projectId: number): Promise<Milestone[]> {
    if (env.useMocks) return mockApi.listMilestones(projectId);
    return apiRequest<Milestone[]>(`/api/milestones/projects/${projectId}`);
  },

  async getMilestone(milestoneId: number): Promise<Milestone> {
    if (env.useMocks) return mockApi.getMilestone(milestoneId);
    return apiRequest<Milestone>(`/api/milestones/${milestoneId}`);
  },

  async createMilestone(
    projectId: number,
    payload: {
      title: string;
      description: string;
      amount: string;
      due_date: string;
      acceptance_criteria: string[];
    },
  ): Promise<Milestone> {
    if (env.useMocks) return mockApi.createMilestone(projectId, payload);
    return apiRequest<Milestone>(`/api/milestones/projects/${projectId}`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async listDeliverables(milestoneId: number): Promise<Deliverable[]> {
    if (env.useMocks) return mockApi.listDeliverables(milestoneId);
    return apiRequest<Deliverable[]>(`/api/milestones/${milestoneId}/deliverables`);
  },

  async submitDeliverable(
    milestoneId: number,
    payload: { description: string; file_urls: string[] },
  ): Promise<Deliverable> {
    if (env.useMocks) return mockApi.submitDeliverable(milestoneId, payload);
    return apiRequest<Deliverable>(`/api/milestones/${milestoneId}/deliverables`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async evaluateDeliverable(deliverableId: number): Promise<Evaluation> {
    const result = env.useMocks
      ? await mockApi.evaluateDeliverable(deliverableId)
      : await apiRequest<Evaluation>(`/api/deliverables/${deliverableId}/evaluate`, {
          method: "POST",
        });
    cacheEvaluation(result);
    return result;
  },

  async submitEvaluationDecision(
    evaluationId: number,
    decision: "accepted" | "revision_requested",
  ): Promise<Evaluation> {
    const result = env.useMocks
      ? await mockApi.submitEvaluationDecision(evaluationId, decision)
      : await apiRequest<Evaluation>(`/api/evaluations/${evaluationId}/decision`, {
          method: "POST",
          body: JSON.stringify({ decision }),
        });
    cacheEvaluation(result);
    return result;
  },
};

