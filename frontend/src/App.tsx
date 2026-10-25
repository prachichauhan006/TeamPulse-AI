import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./auth/AuthContext";
import { ProtectedRoute } from "./auth/ProtectedRoute";
import { WorkspaceProvider } from "./workspace/WorkspaceContext";
import { AppShell } from "./components/AppShell";
import { ToastProvider } from "./components/Toast";
import { Login } from "./pages/Login";
import { Register } from "./pages/Register";
import { Dashboard } from "./pages/Dashboard";
import { Projects } from "./pages/Projects";
import { Tasks } from "./pages/Tasks";
import { TaskDetail } from "./pages/TaskDetail";
import { AIGenerator } from "./pages/AIGenerator";
import { MeetingNotes } from "./pages/MeetingNotes";
import { Documents } from "./pages/Documents";
import { Search } from "./pages/Search";
import { Audit } from "./pages/Audit";
import { WorkspaceSettings } from "./pages/WorkspaceSettings";
import { NotFound } from "./pages/NotFound";

export default function App() {
  return (
    <BrowserRouter>
      <ToastProvider>
        <AuthProvider>
          <WorkspaceProvider>
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />
              <Route element={<ProtectedRoute><AppShell /></ProtectedRoute>}>
                <Route index element={<Dashboard />} />
                <Route path="projects" element={<Projects />} />
                <Route path="tasks" element={<Tasks />} />
                <Route path="tasks/:taskId" element={<TaskDetail />} />
                <Route path="ai-plan" element={<AIGenerator />} />
                <Route path="meeting-notes" element={<MeetingNotes />} />
                <Route path="documents" element={<Documents />} />
                <Route path="search" element={<Search />} />
                <Route path="audit" element={<Audit />} />
                <Route path="workspace" element={<WorkspaceSettings />} />
              </Route>
              <Route path="/app" element={<Navigate to="/" replace />} />
              <Route path="*" element={<NotFound />} />
            </Routes>
          </WorkspaceProvider>
        </AuthProvider>
      </ToastProvider>
    </BrowserRouter>
  );
}
