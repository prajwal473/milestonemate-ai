import { useEffect, useState } from "react";
import type { Payment, PaymentApi } from "./PaymentApi";
import { PaymentStatusBadge } from "./PaymentStatusBadge";

export interface PaymentCancelPageProps { api: PaymentApi }

export function PaymentCancelPage({ api }: PaymentCancelPageProps) {
  const [payment, setPayment] = useState<Payment | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const paymentId = new URLSearchParams(window.location.search).get("payment_id");
    if (!paymentId) { setError("The cancellation link is missing its payment reference."); return; }
    void api.cancelPayment(paymentId)
      .then((result) => { if (!cancelled) setPayment(result); })
      .catch(async (cause) => {
        try {
          const current = await api.getPayment(paymentId);
          if (!cancelled) setPayment(current);
        } catch {
          if (!cancelled) setError(cause instanceof Error ? cause.message : "Could not update payment status.");
        }
      });
    return () => { cancelled = true; };
  }, [api]);

  return (
    <main aria-labelledby="payment-cancel-title" style={{ maxWidth: 640, margin: "3rem auto", padding: 20 }}>
      <h1 id="payment-cancel-title">Checkout cancelled</h1>
      {payment?.provider === "MOCK" && <p role="note" style={{ background: "#fff3c4", padding: 10 }}>SIMULATED PAYMENTS</p>}
      {payment && <PaymentStatusBadge status={payment.status} simulated={payment.provider === "MOCK"} />}
      <p>Your milestone remains unpaid. You can start checkout again when you’re ready.</p>
      {error && <p role="alert">{error}</p>}
    </main>
  );
}
