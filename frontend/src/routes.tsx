import { Navigate, Route, Routes, useParams } from "react-router-dom";
import { ActivityPage } from "./features/activity/ActivityPage";
import { AgreementPage } from "./features/agreement/AgreementPage";
import { LoginPage } from "./features/auth/LoginPage";
import { RegisterPage } from "./features/auth/RegisterPage";
import { RequireAuth } from "./features/auth/RequireAuth";
import { DashboardPage } from "./features/dashboard/DashboardPage";
import { InvitePage } from "./features/invitations/InvitePage";
import { LandingPage } from "./features/landing/LandingPage";
import { MilestoneDetailPage } from "./features/milestones/MilestoneDetailPage";
import { NotFoundPage } from "./features/misc/NotFoundPage";
import { NotificationsPage } from "./features/notifications/NotificationsPage";
import { ProfilePage } from "./features/profile/ProfilePage";
import { NewProjectWizardPage } from "./features/projects/NewProjectWizardPage";
import { ProjectOverviewPage } from "./features/projects/ProjectOverviewPage";
import {
  PaymentCancelHostPage,
  PaymentReturnHostPage,
  ProjectPaymentsPage,
} from "./features/projects/ProjectPaymentsPage";

function ProjectOverviewRoute() {
  const { id } = useParams();
  return <ProjectOverviewPage projectId={Number(id)} />;
}

function AgreementRoute() {
  const { id } = useParams();
  return <AgreementPage projectId={Number(id)} />;
}

function MilestoneRoute() {
  const { id, mid } = useParams();
  return <MilestoneDetailPage projectId={Number(id)} milestoneId={Number(mid)} />;
}

function ProjectPaymentsRoute() {
  const { id } = useParams();
  return <ProjectPaymentsPage projectId={Number(id)} />;
}

function ActivityRoute() {
  const { id } = useParams();
  return <ActivityPage projectId={Number(id)} />;
}

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/invite/:token" element={<InvitePage />} />

      <Route
        path="/dashboard"
        element={
          <RequireAuth>
            <DashboardPage />
          </RequireAuth>
        }
      />
      <Route
        path="/projects"
        element={<Navigate to="/dashboard" replace />}
      />
      <Route
        path="/projects/new"
        element={
          <RequireAuth>
            <NewProjectWizardPage />
          </RequireAuth>
        }
      />
      <Route
        path="/projects/:id"
        element={
          <RequireAuth>
            <ProjectOverviewRoute />
          </RequireAuth>
        }
      />
      <Route
        path="/projects/:id/agreement"
        element={
          <RequireAuth>
            <AgreementRoute />
          </RequireAuth>
        }
      />
      <Route
        path="/projects/:id/milestones/:mid"
        element={
          <RequireAuth>
            <MilestoneRoute />
          </RequireAuth>
        }
      />
      <Route
        path="/projects/:id/payments"
        element={
          <RequireAuth>
            <ProjectPaymentsRoute />
          </RequireAuth>
        }
      />
      <Route
        path="/projects/:id/activity"
        element={
          <RequireAuth>
            <ActivityRoute />
          </RequireAuth>
        }
      />
      <Route
        path="/payments/return"
        element={
          <RequireAuth>
            <PaymentReturnHostPage />
          </RequireAuth>
        }
      />
      <Route
        path="/payments/cancel"
        element={
          <RequireAuth>
            <PaymentCancelHostPage />
          </RequireAuth>
        }
      />
      <Route
        path="/notifications"
        element={
          <RequireAuth>
            <NotificationsPage />
          </RequireAuth>
        }
      />
      <Route
        path="/profile"
        element={
          <RequireAuth>
            <ProfilePage />
          </RequireAuth>
        }
      />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}

