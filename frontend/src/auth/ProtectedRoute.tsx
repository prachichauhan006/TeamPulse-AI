import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { LoadingState } from "../components/ui";
import { useAuth } from "./AuthContext";

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { user, isLoading, sessionExpired } = useAuth();
  const location = useLocation();
  if (isLoading) return <main className="min-h-screen bg-slate-50 p-8"><LoadingState label="Restoring your session…" /></main>;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname, sessionExpired }} />;
  return children;
}
