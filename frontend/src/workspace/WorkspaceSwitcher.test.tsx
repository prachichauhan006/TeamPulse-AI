import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { WorkspaceProvider } from "./WorkspaceContext";
import { WorkspaceSwitcher } from "./WorkspaceSwitcher";

const fetchMock = vi.hoisted(() => vi.fn());
vi.mock("../auth/AuthContext", () => ({ useAuth: () => ({ user: { id: "u1" }, fetchWithAuth: fetchMock }) }));
const workspaces = [{ id: "w1", name: "Workspace One", created_at: "", updated_at: "" }, { id: "w2", name: "Workspace Two", created_at: "", updated_at: "" }];

function renderSwitcher() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}><WorkspaceProvider><WorkspaceSwitcher /></WorkspaceProvider></QueryClientProvider>);
}

describe("WorkspaceSwitcher", () => {
  beforeEach(() => { fetchMock.mockReset(); fetchMock.mockImplementation(async (path: string) => path === "/workspaces" ? workspaces : { items: [{ user_id: "u1", role: "OWNER" }], total: 1 }); });
  it("switches the active workspace and persists the selection", async () => {
    const user = userEvent.setup();
    renderSwitcher();
    const select = await screen.findByLabelText("Select workspace");
    await waitFor(() => expect(select).toHaveValue("w1"));
    await user.selectOptions(select, "w2");
    await waitFor(() => expect(select).toHaveValue("w2"));
    expect(localStorage.getItem("teampulse.selected_workspace")).toBe("w2");
    expect(fetchMock).toHaveBeenCalledWith("/workspaces/w2/members");
  });
});
