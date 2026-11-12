import { describe, expect, it } from "vitest";
import {
  centsToDecimalString,
  formatMoney,
  parseMoneyCents,
  toIsoUtcEndOfDay,
} from "./format";

describe("format helpers & budget math", () => {
  it("formats money with two decimal places", () => {
    expect(formatMoney("1200.00")).toBe("$1,200.00");
    expect(formatMoney(300)).toBe("$300.00");
  });

  it("handles exact cent arithmetic for budget reconciliation", () => {
    const total = parseMoneyCents("1200.00");
    const allocated =
      parseMoneyCents("300.00") + parseMoneyCents("600.00") + parseMoneyCents("300.00");
    expect(total - allocated).toBe(0);
    expect(centsToDecimalString(total - parseMoneyCents("1150.00"))).toBe("50.00");
  });

  it("formats timezone-aware UTC end-of-day dates for milestone creation", () => {
    expect(toIsoUtcEndOfDay("2026-11-23")).toBe("2026-11-23T23:59:59Z");
    expect(toIsoUtcEndOfDay("2026-11-23T12:00:00Z")).toBe("2026-11-23T12:00:00Z");
  });
});

