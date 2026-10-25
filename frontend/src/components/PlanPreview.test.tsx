import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { PlanPreview } from "./PlanPreview";
import type { AIPlan, AIProposal } from "../types";

const proposal: AIProposal<AIPlan> = {
  id: "proposal-1", workspace_id: "workspace-1", proposal_type: "PROJECT_PLAN", status: "PENDING", meeting_note_id: null,
  payload: { project_title: "Launch", summary: "A reviewable launch plan.", risks: ["Timeline risk"], assumptions: ["Owner available"], tasks: [{ key: "T1", title: "Draft brief", description: "Write the brief", priority: "HIGH", suggested_assignee_id: null, suggested_assignee_name: "Alex", due_date: null, depends_on: [] }] },
  result: null, created_by: "user-1", reviewed_by: null, reviewed_at: null, created_at: "", updated_at: "",
};

describe("PlanPreview", () => {
  it("clearly labels AI output as an unapproved preview", () => {
    render(<PlanPreview proposal={proposal} onApprove={vi.fn()} onReject={vi.fn()} />);
    expect(screen.getByTestId("ai-plan-preview")).toHaveTextContent("AI suggestion — not saved yet");
    expect(screen.getByText("Approve and create")).toBeEnabled();
    expect(screen.getByText("Draft brief")).toBeInTheDocument();
  });
});
