import { Link, useParams } from "react-router-dom";
import { MailCheck } from "lucide-react";
import { Button, Card, Copyable } from "../../components/ui";
import { useAuth } from "../auth/useAuth";

export function InvitePage() {
  const { token = "" } = useParams();
  const { user } = useAuth();

  return (
    <div className="mx-auto max-w-lg py-8">
      <Card className="space-y-4">
        <div className="flex items-center gap-2.5">
          <MailCheck className="h-5 w-5 text-brand-600" aria-hidden="true" />
          <h1 className="text-xl font-bold text-ink-900">Project invitation</h1>
        </div>
        <p className="text-sm text-ink-600">
          Direct project invitations in this build use your Freelancer User ID. Sign in and share
          your User ID with the project client so they can assign you on their Project Overview.
        </p>
        {token && <Copyable value={token} label="Invite token" truncate />}

        <div className="flex flex-wrap gap-2 pt-2">
          {user ? (
            <Link to="/profile">
              <Button>View my User ID (#{user.id})</Button>
            </Link>
          ) : (
            <>
              <Link to={`/login?next=${encodeURIComponent(`/invite/${token}`)}`}>
                <Button>Sign in</Button>
              </Link>
              <Link to="/register">
                <Button variant="secondary">Create freelancer account</Button>
              </Link>
            </>
          )}
        </div>
      </Card>
    </div>
  );
}

