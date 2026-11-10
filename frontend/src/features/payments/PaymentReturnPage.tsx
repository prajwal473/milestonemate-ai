import { useEffect, useState } from "react";
import type { Payment, PaymentApi } from "./PaymentApi";
import { PaymentStatusBadge } from "./PaymentStatusBadge";

export interface PaymentReturnPageProps { api: PaymentApi }

export function PaymentReturnPage({ api }: PaymentReturnPageProps) {
  const [payment, setPayment] = useState<Payment | null>(null);
  const [message, setMessage] = useState("Checking payment status…");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function finish() {
      const params = new URLSearchParams(window.location.search);
      const paymentId = params.get("payment_id");
      const orderId = params.get("token");
      if (!paymentId) { setError("The return link is missing its payment reference."); return; }
      try {
        let current = await api.getPayment(paymentId);
        if (params.get("rejected") === "1") {
          setPayment(current);
          setError(current.failure_message || "The simulated payment was declined.");
          return;
        }
        if (current.status !== "COMPLETED" && current.status !== "CAPTURE_PENDING") {
          if (!orderId) throw new Error("PayPal did not return an order reference. You can resume from the payment ledger.");
          current = await api.capturePayment(paymentId, orderId);
        }
        for (let attempt = 0; current.status === "CAPTURE_PENDING" && attempt < 30; attempt += 1) {
          if (cancelled) return;
          setPayment(current);
          setMessage("PayPal is still processing. Checking again…");
          await new Promise((resolve) => window.setTimeout(resolve, 2000));
          current = await api.syncPayment(paymentId);
        }
        if (cancelled) return;
        setPayment(current);
        setMessage(current.status === "COMPLETED" ? "Payment completed successfully." : "Payment status is still pending. You can safely return to this page later.");
      } catch (cause) {
        if (!cancelled) setError(cause instanceof Error ? cause.message : "Could not confirm this payment.");
      }
    }
    void finish();
    return () => { cancelled = true; };
  }, [api]);

  return (
    <main aria-labelledby="payment-return-title" style={{ maxWidth: 640, margin: "3rem auto", padding: 20 }}>
      <h1 id="payment-return-title">Payment status</h1>
      {payment?.provider === "MOCK" && <p role="note" style={{ background: "#fff3c4", padding: 10 }}>SIMULATED PAYMENTS — no real PayPal transaction occurred.</p>}
      {payment && <PaymentStatusBadge status={payment.status} simulated={payment.provider === "MOCK"} />}
      <p aria-live="polite">{error ? "Payment needs attention." : message}</p>
      {error && <div role="alert"><p>{error}</p><p>You can check the payment ledger or try again if the payment was not completed.</p></div>}
      {payment?.failure_message && !error && <p role="alert">{payment.failure_message}</p>}
      {payment?.paypal_capture_id && <p>Capture reference: <code>{payment.paypal_capture_id}</code></p>}
    </main>
  );
}
