import { forwardRef, type InputHTMLAttributes, type SelectHTMLAttributes, type TextareaHTMLAttributes } from "react";

interface FieldWrapperProps {
  id: string;
  label: string;
  error?: string;
  hint?: string;
  required?: boolean;
  children: React.ReactNode;
}

function FieldWrapper({ id, label, error, hint, required, children }: FieldWrapperProps) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="block text-sm font-medium text-ink-900">
        {label}
        {required && <span className="ml-0.5 text-danger-600">*</span>}
      </label>
      {children}
      {error && (
        <p id={`${id}-error`} role="alert" className="text-xs font-medium text-danger-600">
          {error}
        </p>
      )}
      {!error && hint && (
        <p id={`${id}-hint`} className="text-xs text-ink-600">
          {hint}
        </p>
      )}
    </div>
  );
}

const controlBase =
  "w-full rounded-lg border bg-surface px-3 py-2 text-sm text-ink-900 placeholder:text-ink-500 transition duration-150 focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-600/20 disabled:cursor-not-allowed disabled:bg-canvas disabled:text-ink-500";

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  id: string;
  label: string;
  error?: string;
  hint?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { id, label, error, hint, required, className = "", ...rest },
  ref,
) {
  return (
    <FieldWrapper id={id} label={label} error={error} hint={hint} required={required}>
      <input
        ref={ref}
        id={id}
        required={required}
        aria-invalid={Boolean(error) || undefined}
        aria-describedby={error ? `${id}-error` : hint ? `${id}-hint` : undefined}
        className={`${controlBase} min-h-[44px] ${error ? "border-danger-600" : "border-ink-300"} ${className}`}
        {...rest}
      />
    </FieldWrapper>
  );
});

export interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  id: string;
  label: string;
  error?: string;
  hint?: string;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(function Textarea(
  { id, label, error, hint, required, className = "", rows = 4, ...rest },
  ref,
) {
  return (
    <FieldWrapper id={id} label={label} error={error} hint={hint} required={required}>
      <textarea
        ref={ref}
        id={id}
        rows={rows}
        required={required}
        aria-invalid={Boolean(error) || undefined}
        aria-describedby={error ? `${id}-error` : hint ? `${id}-hint` : undefined}
        className={`${controlBase} ${error ? "border-danger-600" : "border-ink-300"} ${className}`}
        {...rest}
      />
    </FieldWrapper>
  );
});

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  id: string;
  label: string;
  error?: string;
  hint?: string;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { id, label, error, hint, required, className = "", children, ...rest },
  ref,
) {
  return (
    <FieldWrapper id={id} label={label} error={error} hint={hint} required={required}>
      <select
        ref={ref}
        id={id}
        required={required}
        aria-invalid={Boolean(error) || undefined}
        className={`${controlBase} min-h-[44px] ${error ? "border-danger-600" : "border-ink-300"} ${className}`}
        {...rest}
      >
        {children}
      </select>
    </FieldWrapper>
  );
});

export interface MoneyInputProps extends Omit<InputProps, "type" | "onChange"> {
  value: string;
  onChange: (value: string) => void;
  currency?: string;
}

export function MoneyInput({
  id,
  label,
  value,
  onChange,
  currency = "USD",
  error,
  hint,
  required,
  ...rest
}: MoneyInputProps) {
  return (
    <FieldWrapper id={id} label={label} error={error} hint={hint} required={required}>
      <div className="relative">
        <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-sm font-medium text-ink-500">
          $
        </span>
        <input
          id={id}
          type="text"
          inputMode="decimal"
          value={value}
          onChange={(e) => {
            const raw = e.target.value;
            if (/^\d*(\.\d{0,2})?$/.test(raw)) {
              onChange(raw);
            }
          }}
          required={required}
          aria-invalid={Boolean(error) || undefined}
          className={`${controlBase} min-h-[44px] pl-7 pr-14 font-semibold tabular-nums ${error ? "border-danger-600" : "border-ink-300"}`}
          {...rest}
        />
        <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-xs font-medium text-ink-500">
          {currency}
        </span>
      </div>
    </FieldWrapper>
  );
}

export function DateInput(props: Omit<InputProps, "type">) {
  return <Input type="date" {...props} />;
}

