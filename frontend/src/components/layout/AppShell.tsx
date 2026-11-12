import { useEffect, useState, type ReactNode } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import {
  Bell,
  FolderKanban,
  LayoutDashboard,
  LogOut,
  Plus,
  ShieldCheck,
  User as UserIcon,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../../api/endpoints";
import { env } from "../../lib/env";
import { Avatar, Badge, Banner, Button } from "../ui";
import { useAuth } from "../../features/auth/useAuth";

export function AppShell({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [offline, setOffline] = useState<boolean>(
    typeof navigator !== "undefined" ? !navigator.onLine : false,
  );

  useEffect(() => {
    const handleOnline = () => setOffline(false);
    const handleOffline = () => setOffline(true);
    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);
    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  const { data: projects = [] } = useQuery({
    queryKey: ["projects"],
    queryFn: api.listProjects,
    enabled: Boolean(user),
    refetchInterval: 15000,
  });

  const actionCount = projects.filter((p) => {
    const s = p.status.toLowerCase();
    return s === "draft" || s === "active";
  }).length;

  const navItems = [
    { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
    { to: "/projects/new", label: "New project", icon: Plus, clientOnly: true },
    { to: "/notifications", label: "Notifications", icon: Bell },
    { to: "/profile", label: "Profile", icon: UserIcon },
  ].filter((item) => !item.clientOnly || user?.role === "client");

  return (
    <div className="flex min-h-screen flex-col bg-canvas text-ink-900">
      <header className="sticky top-0 z-30 border-b border-ink-300/70 bg-surface/95 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6">
          <div className="flex items-center gap-3">
            <Link to={user ? "/dashboard" : "/"} className="flex items-center gap-2.5">
              <span className="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-brand-600 text-white shadow-sm">
                <ShieldCheck className="h-5 w-5" aria-hidden="true" />
              </span>
              <span className="text-base font-bold tracking-tight text-ink-900">
                MilestoneMate <span className="text-brand-600">AI</span>
              </span>
            </Link>
            {user && (
              <Badge tone={user.role === "client" ? "brand" : "ai"} className="hidden sm:inline-flex">
                {user.role === "client" ? "Client" : "Freelancer"}
              </Badge>
            )}
          </div>

          <div className="flex items-center gap-2">
            {user ? (
              <>
                <Link
                  to="/notifications"
                  aria-label="Notifications"
                  className="relative inline-flex min-h-[40px] min-w-[40px] items-center justify-center rounded-lg text-ink-600 hover:bg-canvas hover:text-ink-900"
                >
                  <Bell className="h-5 w-5" />
                  {actionCount > 0 && (
                    <span className="absolute right-1.5 top-1.5 inline-flex h-4 min-w-[16px] items-center justify-center rounded-full bg-brand-600 px-1 text-[10px] font-bold text-white">
                      {actionCount}
                    </span>
                  )}
                </Link>
                <Link
                  to="/profile"
                  className="flex items-center gap-2 rounded-lg px-2 py-1 hover:bg-canvas"
                >
                  <Avatar name={user.name} size="sm" />
                  <span className="hidden text-sm font-medium text-ink-900 md:inline">
                    {user.name}
                  </span>
                </Link>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    logout();
                    navigate("/login");
                  }}
                  icon={<LogOut className="h-4 w-4" />}
                >
                  <span className="hidden sm:inline">Sign out</span>
                </Button>
              </>
            ) : (
              <>
                <Link to="/login">
                  <Button variant="ghost" size="sm">
                    Sign in
                  </Button>
                </Link>
                <Link to="/register">
                  <Button size="sm">Get started</Button>
                </Link>
              </>
            )}
          </div>
        </div>

        {/* Environment transparency banners */}
        {offline && (
          <Banner tone="warning">
            You appear to be offline. Changes may fail until your connection is restored.
          </Banner>
        )}
        {env.useMocks ? (
          <Banner tone="ai">
            DEMO MOCK MODE — running with local simulated API data (VITE_USE_MOCKS=true).
          </Banner>
        ) : (
          <Banner tone="warning">
            {env.paymentsMode === "paypal_sandbox"
              ? "SANDBOX — PayPal Sandbox mode active; no real money moves."
              : "SIMULATED PAYMENTS / SANDBOX — demo environment; no real money moves."}
          </Banner>
        )}
      </header>

      <div className="mx-auto flex w-full max-w-7xl flex-1 gap-6 px-4 py-6 sm:px-6">
        {user && (
          <aside className="hidden w-56 shrink-0 lg:block" aria-label="Primary navigation">
            <nav className="sticky top-28 space-y-1">
              {navItems.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    className={({ isActive }) =>
                      `flex min-h-[44px] items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition ${
                        isActive
                          ? "bg-brand-50 text-brand-700"
                          : "text-ink-600 hover:bg-surface hover:text-ink-900"
                      }`
                    }
                  >
                    <Icon className="h-4 w-4" aria-hidden="true" />
                    <span>{item.label}</span>
                  </NavLink>
                );
              })}

              {projects.length > 0 && (
                <div className="pt-5">
                  <p className="px-3 text-xs font-semibold uppercase tracking-wider text-ink-500">
                    Recent projects
                  </p>
                  <div className="mt-2 space-y-1">
                    {projects.slice(0, 5).map((proj) => (
                      <NavLink
                        key={proj.id}
                        to={`/projects/${proj.id}`}
                        className={({ isActive }) =>
                          `flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium transition ${
                            isActive
                              ? "bg-brand-50 text-brand-700"
                              : "text-ink-600 hover:bg-surface hover:text-ink-900"
                          }`
                        }
                      >
                        <FolderKanban className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                        <span className="truncate">{proj.title}</span>
                      </NavLink>
                    ))}
                  </div>
                </div>
              )}
            </nav>
          </aside>
        )}

        <main className="min-w-0 flex-1 pb-20 lg:pb-6">{children}</main>
      </div>

      {/* Mobile bottom tab bar */}
      {user && (
        <nav
          aria-label="Mobile navigation"
          className="fixed bottom-0 inset-x-0 z-30 flex items-center justify-around border-t border-ink-300/70 bg-surface py-1.5 lg:hidden"
        >
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `flex min-h-[44px] min-w-[56px] flex-col items-center justify-center gap-0.5 rounded-lg px-2 text-[11px] font-medium ${
                    isActive ? "text-brand-600" : "text-ink-600"
                  }`
                }
              >
                <Icon className="h-5 w-5" aria-hidden="true" />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </nav>
      )}

      <footer className="border-t border-ink-300/60 bg-surface py-5 text-xs text-ink-600">
        <div className="mx-auto flex max-w-7xl flex-col items-start justify-between gap-3 px-4 sm:flex-row sm:items-center sm:px-6">
          <p>
            MilestoneMate coordinates agreements and PayPal payments. It is not an escrow service
            and not legal advice. Paid via PayPal only after client approval.
          </p>
          <div className="flex items-center gap-4">
            <a
              href="https://github.com/prajwal473/milestonemate-ai"
              target="_blank"
              rel="noreferrer"
              className="font-medium text-brand-600 hover:underline"
            >
              GitHub
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}

