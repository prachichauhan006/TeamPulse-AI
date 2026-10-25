import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { ProtectedRoute } from "./ProtectedRoute";

vi.mock("./AuthContext", () => ({ useAuth: () => ({ user: null, isLoading: false, sessionExpired: false }) }));

describe("ProtectedRoute", () => {
  it("redirects anonymous users to login and preserves the destination", () => {
    render(<MemoryRouter initialEntries={["/tasks"]}><Routes><Route path="/login" element={<h1>Sign in</h1>} /><Route path="/tasks" element={<ProtectedRoute><h1>Private tasks</h1></ProtectedRoute>} /></Routes></MemoryRouter>);
    expect(screen.getByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Private tasks" })).not.toBeInTheDocument();
  });
});
