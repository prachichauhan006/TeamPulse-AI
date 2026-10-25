import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { RoleGate, WorkspaceProvider, hasPermission } from "./WorkspaceContext";

const fetchMock = vi.hoisted(() => vi.fn());
vi.mock("../auth/AuthContext", () => ({ useAuth: () => ({ user: { id: "viewer-1" }, fetchWithAuth: fetchMock }) }));

describe("permission-restricted controls", () => {
  beforeEach(() => {
    fetchMock.mockReset();
    fetchMock.mockImplementation(async (path: string) => path === "/workspaces"
      ? [{ id: "workspace-1", name: "Demo", created_at: "", updated_at: "" }]
      : { items: [{ id: "membership-1", workspace_id: "workspace-1", user_id: "viewer-1", email: "viewer@example.com", full_name: "Viewer", role: "VIEWER", created_at: "", updated_at: "" }], total: 1 });
  });

  it("hides editor controls from viewers and keeps the permission matrix explicit", async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={client}><WorkspaceProvider><RoleGate permission="edit" fallback={<span>Read-only access</span>}><button>Edit task</button></RoleGate></WorkspaceProvider></QueryClientProvider>);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/workspaces/workspace-1/members"));
    expect(screen.queryByRole("button", { name: "Edit task" })).not.toBeInTheDocument();
    expect(screen.getByText("Read-only access")).toBeInTheDocument();
    expect(hasPermission("VIEWER", "edit")).toBe(false);
    expect(hasPermission("MEMBER", "edit")).toBe(true);
    expect(hasPermission("MEMBER", "manage")).toBe(false);
    expect(hasPermission("ADMIN", "manage")).toBe(true);
  });
});
