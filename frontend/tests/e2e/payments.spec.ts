import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

const apiBase = process.env.E2E_API_BASE_URL ?? "http://localhost:8000";
const webBase = process.env.E2E_WEB_BASE_URL ?? "http://localhost:5173";
const milestoneId = process.env.E2E_MILESTONE_ID;
const email = process.env.E2E_CLIENT_EMAIL;
const password = process.env.E2E_CLIENT_PASSWORD;

type Payment = { id: number; status: string; provider: string; paypal_order_id: string; approve_url: string };

async function makePayment(request: APIRequestContext): Promise<{ payment: Payment; auth: string }> {
  if (!milestoneId || !email || !password) throw new Error("Set E2E_MILESTONE_ID, E2E_CLIENT_EMAIL and E2E_CLIENT_PASSWORD.");
  const login = await request.post(`${apiBase}/api/auth/login`, { data: { email, password } });
  expect(login.ok()).toBeTruthy();
  const auth = `Bearer ${(await login.json()).access_token}`;
  const response = await request.post(`${apiBase}/api/milestones/${milestoneId}/payments`, { headers: { Authorization: auth } });
  expect(response.ok()).toBeTruthy();
  const payment = await response.json() as Payment;
  expect(payment.provider).toBe("MOCK");
  expect(payment.approve_url).toContain("/mock-paypal/checkout");
  return { payment, auth };
}

async function checkout(page: Page, payment: Payment) {
  await page.route(`${webBase}/payments/**`, (route) => route.fulfill({
    status: 200,
    contentType: "text/html",
    body: "<title>Payment return captured</title>",
  }));
  await page.goto(new URL(payment.approve_url, apiBase).toString());
  await expect(page.getByText("SIMULATED PAYMENTS")).toBeVisible();
}

test("mock payment approval completes and records an auditable ledger row", async ({ page, request }) => {
  const { payment, auth } = await makePayment(request);
  await checkout(page, payment);
  await page.getByRole("button", { name: "Approve (SIMULATED)" }).click();
  await expect(page).toHaveURL(new RegExp(`/payments/return\\?payment_id=${payment.id}`));
  const captured = await request.post(`${apiBase}/api/payments/${payment.id}/capture`, {
    headers: { Authorization: auth }, data: { paypal_order_id: payment.paypal_order_id },
  });
  expect(captured.ok()).toBeTruthy();
  expect((await captured.json()).status).toBe("COMPLETED");
  const detail = await request.get(`${apiBase}/api/payments/${payment.id}`, { headers: { Authorization: auth } });
  const data = await detail.json();
  expect(data.events.map((event: { event_type: string }) => event.event_type)).toContain("CAPTURE_COMPLETED");
});

test("buyer rejection is visible and does not mark the milestone paid", async ({ page, request }) => {
  const { payment, auth } = await makePayment(request);
  await checkout(page, payment);
  await page.getByRole("button", { name: "Reject (SIMULATED)" }).click();
  await expect(page).toHaveURL(new RegExp(`/payments/return\\?payment_id=${payment.id}&rejected=1`));
  const detail = await request.get(`${apiBase}/api/payments/${payment.id}`, { headers: { Authorization: auth } });
  expect((await detail.json()).status).toBe("DENIED");
});

test("cancellation permits a fresh payment attempt", async ({ page, request }) => {
  const { payment, auth } = await makePayment(request);
  await checkout(page, payment);
  await page.getByRole("button", { name: "Cancel" }).click();
  await expect(page).toHaveURL(new RegExp(`/payments/cancel\\?payment_id=${payment.id}`));
  const cancelled = await request.get(`${apiBase}/api/payments/${payment.id}`, { headers: { Authorization: auth } });
  expect((await cancelled.json()).status).toBe("CANCELLED");

  const retry = await request.post(`${apiBase}/api/milestones/${milestoneId}/payments`, { headers: { Authorization: auth } });
  expect(retry.ok()).toBeTruthy();
  expect((await retry.json()).id).not.toBe(payment.id);
});
