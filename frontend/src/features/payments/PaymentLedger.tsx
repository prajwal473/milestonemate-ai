import { useCallback, useEffect, useState } from "react";
import type { Payment, PaymentApi, PaymentLedger as PaymentLedgerData } from "./PaymentApi";
import { PaymentStatusBadge } from "./PaymentStatusBadge";

export interface PaymentLedgerProps { projectId: string; api: PaymentApi }

function Timeline({ payment }: { payment: Payment }) {
  return (
    <ol aria-label={`History for payment ${payment.id}`} style={{ margin: "8px 0 16px", paddingLeft: 22 }}>
      {(payment.events ?? []).map((event, index) => (
        <li key={`${event.created_at}-${index}`} style={{ margin: "8px 0" }}>
          <strong>{event.event_type.replaceAll("_", " ")}</strong>
          {event.from_status && event.to_status && <span> · {event.from_status} → {event.to_status}</span>}
          <div><time dateTime={event.created_at}>{new Date(event.created_at).toLocaleString()}</time> · {event.source}</div>
          {event.paypal_ref && <div>Provider reference: <code>{event.paypal_ref}</code></div>}
        </li>
      ))}
      {payment.webhook_verified && <li>PayPal webhook signature verified</li>}
    </ol>
  );
}

export function PaymentLedger({ projectId, api }: PaymentLedgerProps) {
  const [ledger, setLedger] = useState<PaymentLedgerData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const refresh = useCallback(async () => {
    setError(null);
    try { setLedger(await api.getProjectPayments(projectId)); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Could not load payment history."); }
    finally { setLoading(false); }
  }, [api, projectId]);

  useEffect(() => { void refresh(); }, [refresh]);

  return (
    <section aria-labelledby="payment-ledger-title">
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2 id="payment-ledger-title">Payment history</h2>
        <button type="button" onClick={() => void refresh()} disabled={loading}>Refresh</button>
      </header>
      {ledger && <dl style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
        <div><dt>Paid</dt><dd>{ledger.totals.paid} USD</dd></div>
        <div><dt>Pending</dt><dd>{ledger.totals.pending} USD</dd></div>
        <div><dt>Remaining</dt><dd>{ledger.totals.remaining} USD</dd></div>
      </dl>}
      {loading && <p role="status">Loading payment history…</p>}
      {error && <p role="alert">{error}</p>}
      {!loading && !error && ledger?.items.length === 0 && <p>No payments have been started for this project.</p>}
      {ledger && ledger.items.length > 0 && <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead><tr><th scope="col">Payment</th><th scope="col">Amount</th><th scope="col">Status</th><th scope="col">PayPal order</th><th scope="col">Capture</th><th scope="col">Webhook</th><th scope="col">Timeline</th></tr></thead>
          <tbody>{ledger.items.map((payment) => <tr key={payment.id}>
            <th scope="row">{payment.milestone_title ?? `Milestone ${payment.milestone_id}`}</th>
            <td>{payment.amount} {payment.currency}</td>
            <td><PaymentStatusBadge status={payment.status} simulated={payment.provider === "MOCK"} /></td>
            <td><code>{payment.paypal_order_id ?? "—"}</code></td>
            <td><code>{payment.paypal_capture_id ?? "—"}</code></td>
            <td>{payment.webhook_verified ? "Verified" : "Not received"}</td>
            <td><details><summary>View events ({payment.events?.length ?? 0})</summary><Timeline payment={payment} /></details></td>
          </tr>)}</tbody>
        </table>
      </div>}
    </section>
  );
}
