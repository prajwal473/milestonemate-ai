import { env } from "../lib/env";

const TOKEN_STORAGE_KEY = "mm_access_token";

export class ApiError extends Error {
  status: number;
  code: string;
  requestId?: string;
  details?: unknown;

  constructor(
    message: string,
    status: number,
    code = "API_ERROR",
    requestId?: string,
    details?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.requestId = requestId;
    this.details = details;
  }
}

export function getAccessToken(): string | null {
  try {
    return window.localStorage.getItem(TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function setAccessToken(token: string | null): void {
  try {
    if (token) {
      window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
    } else {
      window.localStorage.removeItem(TOKEN_STORAGE_KEY);
    }
  } catch {
    // ignore storage errors in restricted contexts
  }
}

let onUnauthorized: (() => void) | null = null;

export function registerUnauthorizedHandler(handler: () => void): void {
  onUnauthorized = handler;
}

interface RawErrorPayload {
  detail?: string | Array<{ msg?: string; loc?: Array<string | number> }>;
  error?: {
    code?: string;
    message?: string;
    request_id?: string;
    details?: unknown;
  };
}

export async function apiRequest<T>(
  path: string,
  init?: RequestInit & { skipAuthRedirect?: boolean },
): Promise<T> {
  const token = getAccessToken();
  const base = env.apiBaseUrl.replace(/\/$/, "");
  const headers = new Headers(init?.headers);
  headers.set("Accept", "application/json");
  if (init?.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  let response: Response;
  try {
    response = await fetch(`${base}${path}`, {
      ...init,
      headers,
    });
  } catch {
    throw new ApiError(
      "Can't reach the server. Check that the backend is running.",
      0,
      "NETWORK_ERROR",
    );
  }

  const requestId = response.headers.get("X-Request-Id") ?? undefined;
  const text = await response.text();
  let parsed: RawErrorPayload | T | null = null;
  if (text) {
    try {
      parsed = JSON.parse(text) as RawErrorPayload | T;
    } catch {
      parsed = null;
    }
  }

  if (!response.ok) {
    if (response.status === 401 && !init?.skipAuthRedirect) {
      setAccessToken(null);
      onUnauthorized?.();
    }

    const errObj = (parsed ?? {}) as RawErrorPayload;
    let message = `Request failed (${response.status}).`;
    let code = "API_ERROR";

    if (errObj.error?.message) {
      message = errObj.error.message;
      code = errObj.error.code ?? code;
    } else if (typeof errObj.detail === "string") {
      message = errObj.detail;
    } else if (Array.isArray(errObj.detail) && errObj.detail.length > 0) {
      message = errObj.detail
        .map((item) => {
          const field = item.loc?.slice(-1)[0];
          return field ? `${String(field)}: ${item.msg ?? "invalid"}` : (item.msg ?? "Invalid value");
        })
        .join("; ");
      code = "VALIDATION_ERROR";
    }

    throw new ApiError(
      message,
      response.status,
      code,
      errObj.error?.request_id ?? requestId,
      errObj.error?.details,
    );
  }

  return (parsed ?? undefined) as T;
}

