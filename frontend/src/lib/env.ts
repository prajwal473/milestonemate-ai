export const env = {
  apiBaseUrl: (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "",
  useMocks: (import.meta.env.VITE_USE_MOCKS as string | undefined) === "true",
  appEnv: (import.meta.env.VITE_APP_ENV as string | undefined) ?? "local",
  paymentsMode: (import.meta.env.VITE_PAYMENTS_MODE as string | undefined) ?? "mock",
  aiMode: (import.meta.env.VITE_AI_MODE as string | undefined) ?? "live",
} as const;

