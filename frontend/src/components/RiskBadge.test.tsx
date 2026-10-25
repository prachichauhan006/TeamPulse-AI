import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RiskBadge } from "./RiskBadge";

describe("RiskBadge", () => {
  it("shows deterministic dependency risk reasons", () => {
    render(<RiskBadge status="AT_RISK" reasons={["Dependency 'Payment integration' is blocked."]} showReason />);
    expect(screen.getByText("AT RISK")).toBeInTheDocument();
    expect(screen.getByTestId("risk-reasons")).toHaveTextContent("Payment integration");
    expect(screen.getByTestId("risk-reasons")).toHaveTextContent("blocked");
  });
});
