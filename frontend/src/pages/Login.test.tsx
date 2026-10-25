import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { Login } from "./Login";

const loginMock = vi.hoisted(() => vi.fn());
const authState = vi.hoisted(() => ({ user: null, sessionExpired: false }));
vi.mock("../auth/AuthContext", () => ({ useAuth: () => ({ user: authState.user, sessionExpired: authState.sessionExpired, login: loginMock }) }));

describe("Login", () => {
  beforeEach(() => { loginMock.mockReset(); loginMock.mockResolvedValue(undefined); authState.user = null; authState.sessionExpired = false; });
  it("shows the session-expired explanation", () => {
    authState.sessionExpired = true;
    render(<MemoryRouter initialEntries={["/login"]}><Login /></MemoryRouter>);
    expect(screen.getByRole("status")).toHaveTextContent("Your session expired");
  });
  it("signs in and returns to the protected destination", async () => {
    const user = userEvent.setup();
    render(<MemoryRouter initialEntries={[{ pathname: "/login", state: { from: "/tasks" } }]}><Routes><Route path="/login" element={<Login />} /><Route path="/tasks" element={<h1>Private tasks</h1>} /></Routes></MemoryRouter>);
    await user.type(screen.getByLabelText("Email address"), "person@example.com");
    await user.type(screen.getByLabelText("Password"), "correct-horse");
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    expect(loginMock).toHaveBeenCalledWith("person@example.com", "correct-horse");
    expect(await screen.findByRole("heading", { name: "Private tasks" })).toBeInTheDocument();
  });
});
