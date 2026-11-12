import { Link } from "react-router-dom";
import { getPaymentApi } from "../../api/paymentsAdapter";
import { ProjectLayout } from "../../components/layout/ProjectLayout";
import { Button, Card } from "../../components/ui";
import { PaymentCancelPage } from "../payments/PaymentCancelPage";
import { PaymentLedger } from "../payments/PaymentLedger";
import { PaymentReturnPage } from "../payments/PaymentReturnPage";

export function ProjectPaymentsPage({ projectId }: { projectId: number }) {
  const paymentApi = getPaymentApi();
  return (
    <ProjectLayout projectId={projectId} activeTab="payments">
      {() => (
        <Card>
          <PaymentLedger projectId={String(projectId)} api={paymentApi} />
        </Card>
      )}
    </ProjectLayout>
  );
}

export function PaymentReturnHostPage() {
  const paymentApi = getPaymentApi();
  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <Card>
        <PaymentReturnPage api={paymentApi} />
        <div className="mt-4 flex justify-end border-t border-ink-300/60 pt-4">
          <Link to="/dashboard">
            <Button variant="secondary">Back to dashboard</Button>
          </Link>
        </div>
      </Card>
    </div>
  );
}

export function PaymentCancelHostPage() {
  const paymentApi = getPaymentApi();
  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <Card>
        <PaymentCancelPage api={paymentApi} />
        <div className="mt-4 flex justify-end border-t border-ink-300/60 pt-4">
          <Link to="/dashboard">
            <Button variant="secondary">Back to dashboard</Button>
          </Link>
        </div>
      </Card>
    </div>
  );
}

