import { createPaymentApi, type PaymentApi } from "../features/payments/PaymentApi";
import { env } from "../lib/env";
import { getAccessToken } from "./client";
import { createMockPaymentApi } from "./mocks/mockApi";

let singleton: PaymentApi | null = null;

export function getPaymentApi(): PaymentApi {
  if (!singleton) {
    singleton = env.useMocks
      ? createMockPaymentApi()
      : createPaymentApi(env.apiBaseUrl, getAccessToken);
  }
  return singleton;
}

