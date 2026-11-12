import { describe, expect, it } from "vitest";
import { validateDeliverableFiles } from "./fileValidation";

describe("validateDeliverableFiles", () => {
  it("accepts allowed extensions within size and count limits", () => {
    const good = new File(["# Copy"], "copy.md", { type: "text/markdown" });
    const result = validateDeliverableFiles([good], 0);
    expect(result.accepted).toHaveLength(1);
    expect(result.errors).toHaveLength(0);
  });

  it("rejects disallowed extensions and oversized files", () => {
    const badExt = new File(["binary"], "malware.exe", { type: "application/octet-stream" });
    const big = new File([new Uint8Array(6 * 1024 * 1024)], "huge.pdf", {
      type: "application/pdf",
    });
    const result = validateDeliverableFiles([badExt, big], 0);
    expect(result.accepted).toHaveLength(0);
    expect(result.errors).toHaveLength(2);
  });

  it("enforces max 5 files per submission", () => {
    const f1 = new File(["a"], "a.txt");
    const f2 = new File(["b"], "b.txt");
    const result = validateDeliverableFiles([f1, f2], 4, 5);
    expect(result.accepted).toHaveLength(1);
    expect(result.errors[0]).toContain("Maximum 5 files");
  });
});

