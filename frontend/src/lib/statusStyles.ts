export type BadgeTone = "gray" | "brand" | "success" | "warning" | "danger" | "ai";

export interface StatusStyle {
  label: string;
  tone: BadgeTone;
}

const STATUS_MAP: Record<string, StatusStyle> = {
  // Project & Agreement statuses (backend lowercase + doc 08 uppercase)
  draft: { label: "Draft", tone: "gray" },
  in_review: { label: "Awaiting freelancer", tone: "warning" },
  changes_requested: { label: "Changes requested", tone: "warning" },
  rejected: { label: "Changes requested", tone: "warning" },
  superseded: { label: "Superseded", tone: "gray" },
  active: { label: "Active", tone: "brand" },
  completed: { label: "Completed", tone: "success" },
  cancelled: { label: "Cancelled", tone: "gray" },

  // Milestone statuses (backend: pending, submitted, revision_requested, approved, paid + doc 08)
  pending: { label: "In progress", tone: "brand" },
  in_progress: { label: "In progress", tone: "brand" },
  submitted: { label: "Submitted", tone: "brand" },
  revision_requested: { label: "Needs changes", tone: "warning" },
  approved: { label: "Accepted — payment due", tone: "success" },
  accepted: { label: "Accepted — payment due", tone: "success" },
  paid: { label: "Paid", tone: "success" },

  // Deliverable / Evaluation statuses
  evaluating: { label: "AI reviewing", tone: "ai" },
  evaluated: { label: "Ready for decision", tone: "brand" },
  evaluation_failed: { label: "AI unavailable", tone: "danger" },

  // Criteria results (backend lowercase + doc 08 uppercase)
  met: { label: "Met", tone: "success" },
  partially_met: { label: "Partial", tone: "warning" },
  not_met: { label: "Not met", tone: "danger" },
  unverified: { label: "Can't tell", tone: "gray" },
  cannot_determine: { label: "Can't tell", tone: "gray" },

  // Recommendations (backend + doc 08)
  approve: { label: "Recommends accept", tone: "success" },
  meets: { label: "Meets criteria", tone: "success" },
  partially_meets: { label: "Partially meets", tone: "warning" },
  request_revision: { label: "Recommends revision", tone: "warning" },
  does_not_meet: { label: "Does not meet", tone: "danger" },
  manual_review: { label: "Needs manual review", tone: "gray" },
  inconclusive: { label: "Inconclusive", tone: "gray" },

  // Payment statuses
  created: { label: "Preparing payment", tone: "warning" },
  pending_approval: { label: "Waiting for approval", tone: "warning" },
  capture_pending: { label: "PayPal processing", tone: "brand" },
  failed: { label: "Failed", tone: "danger" },
  denied: { label: "Declined", tone: "danger" },
};

export function getStatusStyle(status: string | null | undefined, context?: "agreement" | "milestone"): StatusStyle {
  if (!status) return { label: "Unknown", tone: "gray" };
  const normalized = status.trim().toLowerCase();

  if (context === "agreement" && normalized === "approved") {
    return { label: "Approved", tone: "success" };
  }
  if (context === "milestone" && normalized === "pending") {
    return { label: "Ready for submission", tone: "brand" };
  }
  if (STATUS_MAP[normalized]) {
    return STATUS_MAP[normalized];
  }
  return {
    label: status.replaceAll("_", " "),
    tone: "gray",
  };
}

