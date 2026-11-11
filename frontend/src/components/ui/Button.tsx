import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Loader2 } from "lucide-react";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md" | "lg";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  icon?: ReactNode;
}

const variantClasses: Record<Variant, string> = {
  primary:
    "bg-brand-600 text-white hover:bg-brand-700 shadow-sm disabled:bg-brand-600/50",
  secondary:
    "bg-surface text-ink-900 border border-ink-300 hover:bg-canvas shadow-sm disabled:opacity-50",
  ghost:
    "bg-transparent text-ink-600 hover:bg-ink-300/20 hover:text-ink-900 disabled:opacity-50",
  danger:
    "bg-danger-600 text-white hover:bg-danger-700 shadow-sm disabled:bg-danger-600/50",
};

const sizeClasses: Record<Size, string> = {
  sm: "min-h-[36px] px-3 py-1.5 text-xs",
  md: "min-h-[44px] px-4 py-2 text-sm",
  lg: "min-h-[48px] px-5 py-2.5 text-base",
};

export function Button({
  variant = "primary",
  size = "md",
  loading = false,
  disabled,
  icon,
  children,
  className = "",
  type = "button",
  ...rest
}: ButtonProps) {
  return (
    <button
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={`inline-flex items-center justify-center gap-2 rounded-lg font-medium transition duration-150 focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2 disabled:cursor-not-allowed ${variantClasses[variant]} ${sizeClasses[size]} ${className}`}
      {...rest}
    >
      {loading ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : icon}
      {children}
    </button>
  );
}

