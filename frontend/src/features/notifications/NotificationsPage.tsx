import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Bell, CheckCheck } from "lucide-react";
import { api } from "../../api/endpoints";
import type { NotificationItem } from "../../api/types";
import { Button, Card, EmptyState, Skeleton } from "../../components/ui";
import { formatDateTime } from "../../lib/format";
import { useAuth } from "../auth/useAuth";

const READ_STORAGE_KEY = "mm_read_notifications";

function loadReadIds(): Set<string> {
  try {
    const raw = window.localStorage.getItem(READ_STORAGE_KEY);
    return raw ? new Set(JSON.parse(raw) as string[]) : new Set();
  } catch {
    return new Set();
  }
}

export function NotificationsPage() {
  const { user } = useAuth();
  const [readIds, setReadIds] = useState<Set<string>>(loadReadIds);

  const { data: projects = [], isLoading } = useQuery({
    queryKey: ["projects"],
    queryFn: api.listProjects,
  });

  const items = useMemo<NotificationItem[]>(() => {
    return projects.map((project) => {
      const id = `proj-${project.id}-${project.status}`;
      return {
        id,
        title:
          project.status === "active"
            ? `Project "${project.title}" is active`
            : project.status === "completed"
              ? `Project "${project.title}" completed`
              : `Draft project "${project.title}" awaiting agreement approval`,
        body:
          user?.role === "client"
            ? "Open the project to review milestones, run AI evaluation, or initiate PayPal payment."
            : "Open the project to review the agreement or submit milestone deliverables.",
        link: `/projects/${project.id}`,
        read: readIds.has(id),
        createdAt: project.updated_at,
      };
    });
  }, [projects, readIds, user?.role]);

  function markRead(id: string) {
    setReadIds((prev) => {
      const next = new Set(prev);
      next.add(id);
      try {
        window.localStorage.setItem(READ_STORAGE_KEY, JSON.stringify([...next]));
      } catch {
        // ignore
      }
      return next;
    });
  }

  function markAllRead() {
    const next = new Set(items.map((item) => item.id));
    setReadIds(next);
    try {
      window.localStorage.setItem(READ_STORAGE_KEY, JSON.stringify([...next]));
    } catch {
      // ignore
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-16" />
        <Skeleton className="h-16" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-ink-900">Notifications</h1>
          <p className="text-sm text-ink-600">Actionable updates across your projects.</p>
        </div>
        {items.some((item) => !item.read) && (
          <Button
            size="sm"
            variant="secondary"
            icon={<CheckCheck className="h-4 w-4" />}
            onClick={markAllRead}
          >
            Mark all read
          </Button>
        )}
      </div>

      {items.length === 0 ? (
        <EmptyState
          icon={<Bell className="h-6 w-6" />}
          title="No notifications yet"
          description="Updates appear here as agreements, deliverables, and payments progress."
        />
      ) : (
        <Card padded={false}>
          <ul className="divide-y divide-ink-300/60">
            {items.map((item) => (
              <li key={item.id}>
                <Link
                  to={item.link}
                  onClick={() => markRead(item.id)}
                  className="flex items-start gap-3 px-5 py-4 transition hover:bg-canvas"
                >
                  <span
                    className={`mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full ${
                      item.read ? "bg-transparent" : "bg-brand-600"
                    }`}
                    aria-label={item.read ? "Read" : "Unread"}
                  />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-semibold text-ink-900">{item.title}</p>
                    <p className="mt-0.5 text-xs text-ink-600">{item.body}</p>
                    <p className="mt-1 text-[11px] text-ink-500">
                      {formatDateTime(item.createdAt)}
                    </p>
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}

