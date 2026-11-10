import type { CSSProperties } from "react";
import type { PaymentStatus } from "./PaymentApi";

const labels: Record<PaymentStatus, string> = {
  CREATED: "Preparing payment",
  PENDING_APPROVAL: "Waiting for approval",
  APPROVED: "Approved · finishing payment",
  CAPTURE_PENDING: "PayPal is processing",
  COMPLETED: "Paid",
  FAILED: "Payment failed",
  DENIED: "Payment declined",
  CANCELLED: "Cancelled",
};

const colors: Record<PaymentStatus, string> = {
  CREATED: "#475467",
  PENDING_APPROVAL: "#175cd3",
  APPROVED: "#175cd3",
  CAPTURE_PENDING: "#b54708",
  COMPLETED: "#067647",
  FAILED: "#b42318",
  DENIED: "#b42318",
  CANCELLED: "#667085",
};

export interface PaymentStatusBadgeProps {
  status: PaymentStatus;
  simulated?: boolean;
}

export function PaymentStatusBadge({ status, simulated = false }: PaymentStatusBadgeProps) {
  const style: CSSProperties = {
    display: "inline-flex", alignItems: "center", gap: 6, borderRadius: 999,
    padding: "4px 10px", color: colors[status], background: `${colors[status]}14`,
    fontSize: 13, fontWeight: 600,
  };
  return (
    <span style={style} aria-label={`Payment status: ${labels[status]}${simulated ? ", simulated" : ""}`}>
      {labels[status]}{simulated && <span>(SIMULATED)</span>}
    </span>
  );
}
