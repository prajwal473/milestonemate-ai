export type PaymentStatus =
  | "CREATED"
  | "PENDING_APPROVAL"
  | "APPROVED"
  | "CAPTURE_PENDING"
  | "COMPLETED"
  | "FAILED"
  | "DENIED"
  | "CANCELLED";

export interface PaymentEvent {
  event_type: string;
  from_status: string | null;
  to_status: string | null;
  source: string;
  paypal_ref: string | null;
  created_at: string;
}

export interface Payment {
  id: number;
  milestone_id: number;
  milestone_title?: string | null;
  project_id: number;
  amount: string;
  currency: string;
  status: PaymentStatus;
  provider: "PAYPAL" | "MOCK";
  paypal_order_id: string | null;
  paypal_capture_id: string | null;
  approve_url: string | null;
  created_at: string;
  approved_at: string | null;
  captured_at: string | null;
  failure_code?: string | null;
  failure_message?: string | null;
  payee_mode?: string;
  events?: PaymentEvent[];
  webhook_verified?: boolean;
}

export interface PaymentLedger {
  items: Payment[];
  totals: { paid: string; pending: string; remaining: string };
}

/** The host app supplies its authenticated API adapter here. */
export interface PaymentApi {
  createPayment(milestoneId: string): Promise<Payment>;
  getPayment(paymentId: string): Promise<Payment>;
  capturePayment(paymentId: string, orderId: string): Promise<Payment>;
  cancelPayment(paymentId: string): Promise<Payment>;
  syncPayment(paymentId: string): Promise<Payment>;
  getProjectPayments(projectId: string): Promise<PaymentLedger>;
}

export function createPaymentApi(
  baseUrl: string,
  getAccessToken: () => string | null,
): PaymentApi {
  async function request<T>(path: string, init?: RequestInit): Promise<T> {
    const token = getAccessToken();
    const response = await fetch(`${baseUrl.replace(/\/$/, "")}${path}`, {
      ...init,
      headers: {
        Accept: "application/json",
        ...(init?.body ? { "Content-Type": "application/json" } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...init?.headers,
      },
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail = body?.detail ?? body?.error?.message;
      throw new Error(typeof detail === "string" ? detail : `Payment request failed (${response.status}).`);
    }
    return body as T;
  }

  return {
    createPayment: (milestoneId) => request(`/api/milestones/${encodeURIComponent(milestoneId)}/payments`, { method: "POST" }),
    getPayment: (paymentId) => request(`/api/payments/${encodeURIComponent(paymentId)}`),
    capturePayment: (paymentId, orderId) => request(`/api/payments/${encodeURIComponent(paymentId)}/capture`, {
      method: "POST", body: JSON.stringify({ paypal_order_id: orderId }),
    }),
    cancelPayment: (paymentId) => request(`/api/payments/${encodeURIComponent(paymentId)}/cancel`, { method: "POST" }),
    syncPayment: (paymentId) => request(`/api/payments/${encodeURIComponent(paymentId)}/sync`, { method: "POST" }),
    getProjectPayments: (projectId) => request(`/api/projects/${encodeURIComponent(projectId)}/payments`),
  };
}
