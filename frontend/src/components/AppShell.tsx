import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { useWorkspace } from "../workspace/WorkspaceContext";
import { WorkspaceSwitcher } from "../workspace/WorkspaceSwitcher";
import { Icon } from "./Icon";
import { Badge } from "./ui";

const navigation = [
  { to: "/", label: "Dashboard", icon: "dashboard" as const, end: true },
  { to: "/projects", label: "Projects", icon: "projects" as const },
  { to: "/tasks", label: "Tasks", icon: "tasks" as const },
  { to: "/ai-plan", label: "AI Plan Generator", icon: "sparkles" as const },
  { to: "/meeting-notes", label: "Meeting Notes", icon: "notes" as const },
  { to: "/documents", label: "Documents", icon: "documents" as const },
  { to: "/search", label: "Search & Docs", icon: "search" as const },
  { to: "/audit", label: "Audit Activity", icon: "audit" as const },
  { to: "/workspace", label: "Workspace Settings", icon: "settings" as const },
];

export function AppShell() {
  const { user, logout } = useAuth();
  const { currentRole, selectedWorkspace } = useWorkspace();
  const [mobileOpen, setMobileOpen] = useState(false);
  const navigate = useNavigate();
  async function handleLogout() { await logout(); navigate("/login", { replace: true }); }
  const sidebar = (
    <div className="flex h-full flex-col bg-white">
      <div className="flex h-[4.5rem] items-center gap-3 border-b border-slate-100 px-5"><div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-indigo-600 text-white shadow-lg shadow-indigo-200"><Icon name="sparkles" className="h-5 w-5" /></div><div><p className="font-bold tracking-tight text-slate-950">TeamPulse AI</p><p className="text-[11px] text-slate-400">AI Operating System</p></div></div>
      <div className="px-5 pb-2 pt-5 text-[10px] font-bold uppercase tracking-[0.16em] text-slate-400">Workspace</div>
      <nav className="flex-1 space-y-1 overflow-y-auto px-3 pb-4" aria-label="Main navigation">{navigation.map((item) => <NavLink key={item.to} to={item.to} end={item.end} onClick={() => setMobileOpen(false)} className={({ isActive }) => `nav-link ${isActive ? "nav-link-active" : ""}`}><Icon name={item.icon} className="h-[18px] w-[18px] shrink-0" /><span>{item.label}</span></NavLink>)}</nav>
      <div className="border-t border-slate-100 p-4"><div className="rounded-2xl bg-slate-50 p-3"><div className="flex items-center gap-2"><span className="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-100 text-xs font-bold text-indigo-700">{user?.full_name?.split(" ").map((part) => part[0]).join("").slice(0, 2).toUpperCase()}</span><div className="min-w-0"><p className="truncate text-sm font-semibold text-slate-800">{user?.full_name}</p><p className="truncate text-[11px] text-slate-500">{user?.email}</p></div></div>{currentRole && <div className="mt-2"><Badge tone="indigo">{currentRole}</Badge></div>}</div><button type="button" onClick={() => void handleLogout()} className="nav-link mt-2 w-full text-rose-600 hover:bg-rose-50 hover:text-rose-700"><Icon name="logout" className="h-5 w-5" /> Sign out</button></div>
    </div>
  );
  return (
    <div className="min-h-screen bg-[#f6f7fb]"><aside className="fixed inset-y-0 left-0 z-30 hidden w-64 border-r border-slate-200/80 lg:block">{sidebar}</aside>{mobileOpen && <div className="fixed inset-0 z-50 lg:hidden"><button className="absolute inset-0 bg-slate-950/40" aria-label="Close navigation" onClick={() => setMobileOpen(false)} /><aside className="relative h-full w-72 max-w-[85vw] shadow-2xl">{sidebar}</aside></div>}<div className="lg:pl-64"><header className="sticky top-0 z-20 border-b border-slate-200/80 bg-white/90 backdrop-blur"><div className="flex min-h-[4.5rem] items-center gap-3 px-4 py-3 sm:px-6 lg:px-8"><button type="button" className="rounded-xl p-2 hover:bg-slate-100 lg:hidden" onClick={() => setMobileOpen(true)} aria-label="Open navigation"><Icon name="menu" className="h-6 w-6" /></button><div className="min-w-0 flex-1 sm:max-w-xs"><WorkspaceSwitcher /></div><div className="ml-auto hidden text-right sm:block"><p className="text-[11px] text-slate-400">Current workspace</p><p className="max-w-56 truncate text-sm font-semibold text-slate-800">{selectedWorkspace?.name ?? "Create your first workspace"}</p></div></div></header><main className="mx-auto max-w-[1600px] p-4 sm:p-6 lg:p-8"><Outlet /></main></div></div>
  );
}
