import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StatusBadge } from "./Badge";

describe("StatusBadge", () => {
  it("renders human-friendly labels for backend statuses", () => {
    render(<StatusBadge status="approved" context="milestone" />);
    expect(screen.getByText("Accepted — payment due")).toBeInTheDocument();
  });

  it("renders approved label in agreement context", () => {
    render(<StatusBadge status="approved" context="agreement" />);
    expect(screen.getByText("Approved")).toBeInTheDocument();
  });
});

