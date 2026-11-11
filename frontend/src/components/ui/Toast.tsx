import { useCallback, useState, type ReactNode } from "react";
import { AlertCircle, CheckCircle2, Info, X } from "lucide-react";
import { ToastContext, type ToastEntry } from "./toastContext";

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastEntry[]>([]);

  const dismiss = useCallback((id: number) => {
    setToasts((prev) => prev.filter((item) => item.id !== id));
  }, []);

  const pushToast = useCallback(
    (toast: Omit<ToastEntry, "id">) => {
      const id = Date.now() + Math.floor(Math.random() * 1000);
      setToasts((prev) => [...prev, { ...toast, id }]);
      window.setTimeout(() => {
        dismiss(id);
      }, 4500);
    },
    [dismiss],
  );

  return (
    <ToastContext.Provider value={{ pushToast }}>
      {children}
      <div
        aria-live="polite"
        className="pointer-events-none fixed bottom-20 right-4 z-50 flex w-full max-w-sm flex-col gap-2 lg:bottom-4"
      >
        {toasts.map((toast) => {
          const Icon =
            toast.tone === "success"
              ? CheckCircle2
              : toast.tone === "error"
                ? AlertCircle
                : Info;
          const border =
            toast.tone === "success"
              ? "border-emerald-200 bg-success-50 text-ink-900"
              : toast.tone === "error"
                ? "border-red-200 bg-danger-50 text-ink-900"
                : "border-brand-100 bg-surface text-ink-900";
          const iconColor =
            toast.tone === "success"
              ? "text-success-600"
              : toast.tone === "error"
                ? "text-danger-600"
                : "text-brand-600";

          return (
            <div
              key={toast.id}
              className={`pointer-events-auto flex items-start gap-3 rounded-xl border p-3.5 shadow-lg ${border}`}
            >
              <Icon className={`mt-0.5 h-5 w-5 shrink-0 ${iconColor}`} aria-hidden="true" />
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold">{toast.title}</p>
                {toast.description && (
                  <p className="mt-0.5 text-xs text-ink-600">{toast.description}</p>
                )}
              </div>
              <button
                type="button"
                onClick={() => dismiss(toast.id)}
                aria-label="Dismiss notification"
                className="rounded p-1 text-ink-500 hover:text-ink-900"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}
