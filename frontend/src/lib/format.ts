export function formatMoney(
  value: string | number | null | undefined,
  currency = "USD",
): string {
  const numeric = typeof value === "string" ? Number.parseFloat(value) : (value ?? 0);
  const safe = Number.isFinite(numeric) ? numeric : 0;
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(safe);
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(date);
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}

export function toIsoUtcEndOfDay(dateInput: string): string {
  if (!dateInput) return new Date().toISOString();
  if (dateInput.includes("T")) {
    return dateInput.endsWith("Z") || /[+-]\d{2}:\d{2}$/.test(dateInput)
      ? dateInput
      : `${dateInput}Z`;
  }
  return `${dateInput}T23:59:59Z`;
}

export function toDateInputValue(isoValue: string | null | undefined): string {
  if (!isoValue) return "";
  return isoValue.slice(0, 10);
}

export function parseMoneyCents(value: string | number | null | undefined): number {
  const num = typeof value === "string" ? Number.parseFloat(value) : (value ?? 0);
  if (!Number.isFinite(num)) return 0;
  return Math.round(num * 100);
}

export function centsToDecimalString(cents: number): string {
  return (cents / 100).toFixed(2);
}

export function initialsFromName(name: string | null | undefined): string {
  if (!name) return "?";
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
}

