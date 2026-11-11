import { createContext, useContext } from "react";

export type ToastTone = "success" | "error" | "info";

export interface ToastEntry {
  id: number;
  tone: ToastTone;
  title: string;
  description?: string;
}

export interface ToastContextValue {
  pushToast: (toast: Omit<ToastEntry, "id">) => void;
}

export const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error("useToast must be used within ToastProvider");
  }
  return ctx;
}
