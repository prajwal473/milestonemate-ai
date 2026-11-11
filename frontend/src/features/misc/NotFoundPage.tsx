import { Link } from "react-router-dom";
import { Button, EmptyState } from "../../components/ui";
import { useAuth } from "../auth/useAuth";

export function NotFoundPage() {
  const { user } = useAuth();
  return (
    <div className="mx-auto max-w-xl py-12">
      <EmptyState
        title="Page not found"
        description="The page you requested does not exist or has moved."
        action={
          <Link to={user ? "/dashboard" : "/"}>
            <Button>Back to {user ? "dashboard" : "home"}</Button>
          </Link>
        }
      />
    </div>
  );
}

