import { describe, expect, it } from "vitest";
import { getStatusStyle } from "./statusStyles";

describe("getStatusStyle", () => {
  it("maps agreement statuses accurately", () => {
    expect(getStatusStyle("draft", "agreement")).toEqual({ label: "Draft", tone: "gray" });
    expect(getStatusStyle("approved", "agreement")).toEqual({
      label: "Approved",
      tone: "success",
    });
    expect(getStatusStyle("rejected", "agreement")).toEqual({
      label: "Changes requested",
      tone: "warning",
    });
  });

  it("maps milestone statuses accurately", () => {
    expect(getStatusStyle("pending", "milestone")).toEqual({
      label: "Ready for submission",
      tone: "brand",
    });
    expect(getStatusStyle("submitted", "milestone")).toEqual({
      label: "Submitted",
      tone: "brand",
    });
    expect(getStatusStyle("approved", "milestone")).toEqual({
      label: "Accepted — payment due",
      tone: "success",
    });
    expect(getStatusStyle("paid", "milestone")).toEqual({
      label: "Paid",
      tone: "success",
    });
  });

  it("maps payment and evaluation statuses", () => {
    expect(getStatusStyle("PENDING_APPROVAL").tone).toBe("warning");
    expect(getStatusStyle("COMPLETED").tone).toBe("success");
    expect(getStatusStyle("FAILED").tone).toBe("danger");
    expect(getStatusStyle("met").tone).toBe("success");
    expect(getStatusStyle("unverified").tone).toBe("gray");
  });
});

