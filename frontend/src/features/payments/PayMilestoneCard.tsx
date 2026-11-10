import { useState } from "react";
import type { Payment, PaymentApi } from "./PaymentApi";
import { PaymentStatusBadge } from "./PaymentStatusBadge";

export interface PayMilestoneCardProps {
  projectId: string;
  milestone: { id: string; title: string; amount: string; status: string };
  viewerRole: "CLIENT" | "FREELANCER";
  api: PaymentApi;
}

export function PayMilestoneCard({ milestone, viewerRole, api }: PayMilestoneCardProps) {
  const [payment, setPayment] = useState<Payment | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const accepted = ["ACCEPTED", "approved"].includes(milestone.status);

  async function beginPayment() {
    setBusy(true);
    setError(null);
    try {
      const created = await api.createPayment(milestone.id);
      setPayment(created);
      if (created.approve_url) window.location.assign(created.approve_url);
      else setError("The payment provider did not return a checkout link.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not start this payment.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-labelledby={`payment-${milestone.id}`} style={{ border: "1px solid #eaecf0", borderRadius: 12, padding: 18 }}>
      <h3 id={`payment-${milestone.id}`}>Pay for {milestone.title}</h3>
      <p>{milestone.amount} USD</p>
      {payment?.provider === "MOCK" && <p role="note" style={{ background: "#fff3c4", padding: 10 }}>SIMULATED PAYMENTS — no real money moves.</p>}
      {payment && <PaymentStatusBadge status={payment.status} simulated={payment.provider === "MOCK"} />}
      {!payment && viewerRole === "FREELANCER" && <p>Waiting for the client to pay this accepted milestone.</p>}
      {!payment && viewerRole === "CLIENT" && accepted && (
        <button type="button" onClick={beginPayment} disabled={busy} aria-busy={busy}>
          {busy ? "Preparing checkout…" : "Pay milestone"}
        </button>
      )}
      {!accepted && !payment && <p>Payment becomes available after the milestone is accepted.</p>}
      {error && <p role="alert">{error}</p>}
    </section>
  );
}
