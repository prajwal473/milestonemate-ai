import { useState } from "react";
import { UserCheck } from "lucide-react";
import { Avatar, Badge, Card, Copyable, Input } from "../../components/ui";
import { useAuth } from "../auth/useAuth";

export function ProfilePage() {
  const { user } = useAuth();
  const [paypalEmail, setPaypalEmail] = useState("");

  if (!user) return null;

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-ink-900">Account profile</h1>
        <p className="mt-0.5 text-sm text-ink-600">
          Share your User ID with a project owner so they can assign you to projects.
        </p>
      </div>

      <Card className="space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-ink-300/60 pb-5">
          <div className="flex items-center gap-3.5">
            <Avatar name={user.name} />
            <div>
              <h2 className="text-lg font-semibold text-ink-900">{user.name}</h2>
              <p className="text-sm text-ink-600">{user.email}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge tone={user.role === "client" ? "brand" : "ai"}>
              {user.role === "client" ? "Client" : "Freelancer"}
            </Badge>
            <Badge tone={user.is_active ? "success" : "gray"}>
              {user.is_active ? "Active" : "Inactive"}
            </Badge>
          </div>
        </div>

        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase text-ink-500">Your User ID</p>
          <Copyable value={String(user.id)} label="User ID" />
          <p className="flex items-center gap-1.5 text-xs text-ink-600">
            <UserCheck className="h-3.5 w-3.5 text-brand-600" />
            Clients use this numeric ID on Project Overview to assign a freelancer.
          </p>
        </div>

        <div className="border-t border-ink-300/60 pt-4">
          <Input
            id="profile-paypal-email"
            label="PayPal Sandbox email (informational)"
            type="email"
            value={paypalEmail}
            onChange={(e) => setPaypalEmail(e.target.value)}
            placeholder="sandbox-payee@business.example.com"
            hint="Only used if direct payee mode is enabled; in demo_merchant mode PayPal Sandbox routes to the demo merchant."
          />
        </div>
      </Card>
    </div>
  );
}

