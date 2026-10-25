import { MemoryRouter } from "react-router-dom";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { KanbanBoard, handleKanbanDragEnd } from "./KanbanBoard";
import type { TaskView } from "../types";

const task: TaskView = {
  id: "task-1", workspace_id: "workspace-1", project_id: "project-1", title: "Build Authentication", description: "Secure sign-in", status: "TODO", priority: "HIGH", assignee_id: "user-1", due_date: "2027-01-08", created_by: "user-1", version: 1, created_at: "2027-01-01T00:00:00Z", updated_at: "2027-01-01T00:00:00Z",
  project_title: "Placement Preparation Platform", assignee_name: "Demo Member", dependency_ids: [], risk_status: "ON_TRACK", risk_reasons: [],
};

function dragEvent(over: string | null) {
  return { active: { id: task.id }, over: over ? { id: over } : null } as unknown as Parameters<typeof handleKanbanDragEnd>[0];
}

function renderBoard(canEdit: boolean, onStatusChange = vi.fn()) {
  render(<MemoryRouter><KanbanBoard tasks={[task]} canEdit={canEdit} onStatusChange={onStatusChange} /></MemoryRouter>);
  return onStatusChange;
}

describe("KanbanBoard drag permissions and status updates", () => {
  it("calls the status-update callback for a permitted cross-column drop", () => {
    const onStatusChange = vi.fn();
    handleKanbanDragEnd(dragEvent("DONE"), [task], true, onStatusChange);
    expect(onStatusChange).toHaveBeenCalledOnce();
    expect(onStatusChange).toHaveBeenCalledWith(task, "DONE");
  });

  it("does not update status for a same-column drop", () => {
    const onStatusChange = vi.fn();
    handleKanbanDragEnd(dragEvent("TODO"), [task], true, onStatusChange);
    expect(onStatusChange).not.toHaveBeenCalled();
  });

  it("does not call the status-update callback for a viewer drop", () => {
    const onStatusChange = vi.fn();
    handleKanbanDragEnd(dragEvent("DONE"), [task], false, onStatusChange);
    expect(onStatusChange).not.toHaveBeenCalled();
  });

  it("renders an enabled drag handle for an editor", () => {
    renderBoard(true);
    expect(screen.getByRole("button", { name: "Drag Build Authentication" })).toBeEnabled();
    expect(screen.getByRole("combobox", { name: "Status for Build Authentication" })).toHaveValue("TODO");
    expect(screen.getByTestId("kanban-column-TODO")).toHaveAttribute("data-drop-column", "TODO");
    expect(screen.getByText("Build Authentication").closest("article")).toHaveAttribute("data-draggable", "true");
  });

  it("calls the status-update callback when an editor changes the card status", () => {
    const onStatusChange = renderBoard(true);
    fireEvent.change(screen.getByRole("combobox", { name: "Status for Build Authentication" }), { target: { value: "IN_PROGRESS" } });
    expect(onStatusChange).toHaveBeenCalledOnce();
    expect(onStatusChange).toHaveBeenCalledWith(task, "IN_PROGRESS");
  });

  it("disables drag handles and identifies read-only mode for a viewer", () => {
    const onStatusChange = renderBoard(false);
    expect(screen.getByRole("button", { name: "Drag disabled for Build Authentication" })).toBeDisabled();
    expect(screen.queryByRole("combobox", { name: "Status for Build Authentication" })).not.toBeInTheDocument();
    expect(screen.getByText("Build Authentication").closest("article")).toHaveAttribute("data-draggable", "false");
    expect(screen.getByText(/read-only access/)).toBeInTheDocument();
    expect(onStatusChange).not.toHaveBeenCalled();
  });
});
