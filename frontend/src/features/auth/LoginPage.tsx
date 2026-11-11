import { useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Eye, EyeOff, Lock } from "lucide-react";
import { Button, Card, Input, useToast } from "../../components/ui";
import { env } from "../../lib/env";
import { useAuth } from "./useAuth";

export function LoginPage() {
  const { login } = useAuth();
  const { pushToast } = useToast();
  const navigate = useNavigate();
  const [params] = useSearchParams();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email.trim(), password);
      pushToast({ tone: "success", title: "Signed in" });
      const next = params.get("next");
      navigate(next && next.startsWith("/") ? next : "/dashboard", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not sign in.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-md py-8">
      <Card>
        <div className="mb-6 space-y-1 text-center">
          <div className="mx-auto mb-3 inline-flex h-11 w-11 items-center justify-center rounded-full bg-brand-50 text-brand-600">
            <Lock className="h-5 w-5" aria-hidden="true" />
          </div>
          <h1 className="text-2xl font-bold text-ink-900">Sign in to MilestoneMate</h1>
          <p className="text-sm text-ink-600">
            Coordinate milestone agreements, AI reviews, and PayPal payments.
          </p>
        </div>

        <form onSubmit={(e) => void handleSubmit(e)} className="space-y-4">
          <Input
            id="login-email"
            label="Email address"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
          />

          <div className="relative">
            <Input
              id="login-password"
              label="Password"
              type={showPassword ? "text" : "password"}
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password"
            />
            <button
              type="button"
              onClick={() => setShowPassword((prev) => !prev)}
              aria-label={showPassword ? "Hide password" : "Show password"}
              className="absolute right-2.5 top-[34px] rounded p-1.5 text-ink-500 hover:text-ink-900"
            >
              {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>

          {error && (
            <p
              role="alert"
              className="rounded-lg border border-red-200 bg-danger-50 px-3 py-2 text-xs font-medium text-danger-700"
            >
              {error}
            </p>
          )}

          <Button type="submit" loading={submitting} className="w-full">
            Sign in
          </Button>
        </form>

        {env.useMocks && (
          <div className="mt-5 rounded-lg border border-brand-100 bg-brand-50/60 p-3 text-xs text-ink-700">
            <p className="font-semibold text-brand-700">Quick mock sign-in</p>
            <div className="mt-2 flex flex-wrap gap-2">
              <Button
                size="sm"
                variant="secondary"
                onClick={() => {
                  setEmail("client@demo.milestonemate.test");
                  setPassword("Demo-Client-123!");
                }}
              >
                Fill Client
              </Button>
              <Button
                size="sm"
                variant="secondary"
                onClick={() => {
                  setEmail("freelancer@demo.milestonemate.test");
                  setPassword("Demo-Freelancer-123!");
                }}
              >
                Fill Freelancer
              </Button>
            </div>
          </div>
        )}

        <p className="mt-5 text-center text-sm text-ink-600">
          Don&apos;t have an account?{" "}
          <Link to="/register" className="font-semibold text-brand-600 hover:underline">
            Create one
          </Link>
        </p>
      </Card>
    </div>
  );
}

