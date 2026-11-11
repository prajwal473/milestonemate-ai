export type UserRole = "client" | "freelancer";

export interface User {
  id: number;
  name: string;
  email: string;
  role: UserRole;
  is_active: boolean;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface Project {
  id: number;
  title: string;
  description: string;
  budget: string;
  currency: string;
  status: string;
  client_id: number;
  freelancer_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface AgreementPlannedMilestone {
  title: string;
  description: string;
  amount: string;
  due_date: string;
  acceptance_criteria: string[];
}

export interface AgreementContent {
  title?: string;
  summary?: string;
  scope_in?: string[];
  scope_out?: string[];
  assumptions?: string[];
  payment_terms?: string;
  revision_policy?: string;
  total_amount?: string;
  origin?: "AI" | "TEMPLATE" | "MANUAL";
  planned_milestones?: AgreementPlannedMilestone[];
  [key: string]: unknown;
}

export interface Agreement {
  id: number;
  project_id: number;
  version: number;
  content: AgreementContent;
  status: string;
  client_approved_at: string | null;
  freelancer_approved_at: string | null;
}

export interface Milestone {
  id: number;
  project_id: number;
  agreement_id: number | null;
  title: string;
  description: string;
  amount: string;
  due_date: string;
  acceptance_criteria: string[];
  status: string;
}

export interface Deliverable {
  id: number;
  milestone_id: number;
  submitted_by_id: number;
  description: string;
  file_urls: string[];
  status: string;
  created_at: string;
  updated_at: string;
}

export interface EvaluationCriterionResult {
  criterion: string;
  status: "met" | "partially_met" | "not_met" | "unverified" | string;
  evidence: string;
}

export interface EvaluationFindings {
  summary?: string;
  criteria_results?: EvaluationCriterionResult[];
  missing_requirements?: string[];
}

export interface Evaluation {
  id: number;
  deliverable_id: number;
  model_name: string | null;
  score: string | number | null;
  findings: EvaluationFindings;
  recommendation: "approve" | "request_revision" | "manual_review" | string;
  human_decision: "accepted" | "revision_requested" | null;
}

export interface HealthStatus {
  status: string;
  service: string;
  database: string;
  timestamp: string;
}

export interface AppConfig {
  ai_mode: "mock" | "live";
  payments_mode: "mock" | "paypal_sandbox" | "live";
  payee_mode: string;
  env: string;
}

export interface ActivityEvent {
  id: string;
  category: "agreement" | "deliverable" | "payment" | "project";
  actorType: "USER" | "AI" | "PAYPAL" | "SYSTEM";
  action: string;
  description: string;
  createdAt: string;
  reference?: string | null;
}

export interface NotificationItem {
  id: string;
  title: string;
  body: string;
  link: string;
  read: boolean;
  createdAt: string;
}

