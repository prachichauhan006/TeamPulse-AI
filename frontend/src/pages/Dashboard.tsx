import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "../auth/AuthContext";
import { usePermissions, useWorkspace } from "../workspace/WorkspaceContext";
import { useTaskViews } from "../hooks/useTaskViews";
import type { Paginated, Project, Task, WeeklySummary } from "../types";
import { DuplicateSuggestions } from "../components/DuplicateSuggestions";
import { WorkspaceForm } from "../components/WorkspaceForm";
import { ProjectForm } from "../components/ProjectForm";
import { Icon } from "../components/Icon";
import { EmptyState, ErrorState, LoadingState } from "../components/ui";
import { RiskDistribution } from "../components/RiskDistribution";
import { PriorityBadge, RiskPill } from "../components/StatusBadge";
import { formatDate } from "../lib/api";

function greeting() {
  const hour = new Date().getHours();
  return hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";
}

export function Dashboard() {
  const { selectedWorkspace, workspaces, isLoading: workspaceLoading } = useWorkspace();
  const { fetchWithAuth, user } = useAuth();
  const { canManage } = usePermissions();
  const [workspaceForm, setWorkspaceForm] = useState(false);
  const [projectForm, setProjectForm] = useState(false);
  const workspaceId = selectedWorkspace?.id;
  const projects = useQuery({ queryKey: ["projects", workspaceId, "dashboard"], queryFn: () => fetchWithAuth<Paginated<Project>>(`/workspaces/${workspaceId}/projects?page_size=100`), enabled: Boolean(workspaceId) });
  const tasks = useQuery({ queryKey: ["tasks", workspaceId, "dashboard"], queryFn: () => fetchWithAuth<Paginated<Task>>(`/workspaces/${workspaceId}/tasks?page_size=100`), enabled: Boolean(workspaceId) });
  const enrichment = useTaskViews(tasks.data?.items ?? [], projects.data?.items ?? []);
  const items = enrichment.views;
  const summary = useQuery({ queryKey: ["weekly-summary", workspaceId], queryFn: () => fetchWithAuth<WeeklySummary>(`/workspaces/${workspaceId}/ai/weekly-summary`), enabled: Boolean(workspaceId) });

  if (workspaceLoading) return <LoadingState label="Loading your workspaces…" />;
  if (!workspaces.length) return <><EmptyState title="Welcome to TeamPulse AI" description="Create a workspace to bring projects, tasks, documents, and AI-assisted planning together." action={<button className="btn-primary" onClick={() => setWorkspaceForm(true)}>Create your first workspace</button>} />{workspaceForm && <WorkspaceForm onClose={() => setWorkspaceForm(false)} />}</>;

  const firstName = user?.full_name.split(" ")[0] ?? "there";
  const stats = [
    { label: "Total projects", value: projects.data?.total ?? 0, icon: "projects" as const, tone: "bg-indigo-50 text-indigo-600" },
    { label: "Open tasks", value: items.filter((task) => task.status !== "DONE").length, icon: "tasks" as const, tone: "bg-sky-50 text-sky-600" },
    { label: "At risk", value: items.filter((task) => task.risk_status === "AT_RISK" || task.risk_status === "OVERDUE").length, icon: "warning" as const, tone: "bg-amber-50 text-amber-600" },
    { label: "Blocked tasks", value: items.filter((task) => task.risk_status === "BLOCKED" || task.status === "BLOCKED").length, icon: "shield" as const, tone: "bg-rose-50 text-rose-600" },
  ];
  const deadlines = items.filter((task) => task.status !== "DONE" && task.due_date).sort((a, b) => (a.due_date ?? "").localeCompare(b.due_date ?? "")).slice(0, 5);
  const attention = items.filter((task) => task.risk_status === "BLOCKED" || task.risk_status === "AT_RISK" || task.risk_status === "OVERDUE").sort((a, b) => Number(a.risk_status !== "BLOCKED") - Number(b.risk_status !== "BLOCKED")).slice(0, 5);

  return (
    <div className="space-y-6">
      <section className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
        <div><p className="text-sm font-medium text-indigo-600">{selectedWorkspace?.name}</p><h1 className="mt-1 text-3xl font-bold tracking-tight text-slate-950 sm:text-4xl">{greeting()}, {firstName} <span aria-hidden="true">👋</span></h1><p className="mt-2 text-sm leading-6 text-slate-500">Here’s what’s happening across your workspace today.</p></div>
        {canManage && <div className="flex flex-wrap gap-2"><button className="btn-secondary" onClick={() => setProjectForm(true)}><Icon name="plus" />New project</button><Link to="/ai-plan" className="btn-primary"><Icon name="sparkles" />Generate AI plan</Link></div>}
      </section>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{stats.map((stat) => <div key={stat.label} className="card flex items-center gap-4 p-4"><div className={`rounded-xl p-3 ${stat.tone}`}><Icon name={stat.icon} className="h-5 w-5" /></div><div><p className="text-2xl font-bold tracking-tight text-slate-950">{stat.value}</p><p className="mt-0.5 text-xs font-medium text-slate-500">{stat.label}</p></div></div>)}</div>
      <div className="grid gap-6 xl:grid-cols-[1.45fr_1fr]">
        <section className="card relative overflow-hidden"><div className="absolute right-0 top-0 h-28 w-28 rounded-bl-full bg-indigo-50/70" aria-hidden="true" /><div className="relative flex items-start justify-between"><div><div className="flex items-center gap-2"><span className="rounded-lg bg-indigo-50 p-2 text-indigo-600"><Icon name="sparkles" className="h-4 w-4" /></span><h2 className="text-lg font-semibold text-slate-900">AI Briefing</h2></div><p className="mt-2 text-xs font-medium uppercase tracking-wider text-slate-400">Weekly project summary</p></div><span className="rounded-full border border-slate-200 px-2.5 py-1 text-[10px] font-semibold text-slate-500">REVIEWABLE</span></div>
          {summary.isLoading ? <LoadingState label="Preparing your team briefing…" /> : summary.isError ? <ErrorState message="The briefing isn’t available right now. Your project data is unaffected." onRetry={() => void summary.refetch()} /> : summary.data ? <div className="relative mt-5 space-y-5"><p className="text-sm leading-7 text-slate-700">{summary.data.summary}</p><div><h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">Highlights</h3><ul className="mt-2 space-y-2 text-sm text-slate-600">{summary.data.highlights.map((item) => <li key={item} className="flex gap-2"><Icon name="check" className="mt-0.5 h-4 w-4 shrink-0 text-emerald-500" />{item}</li>)}</ul></div><div className="rounded-xl bg-indigo-50/60 p-4"><h3 className="text-xs font-semibold uppercase tracking-wider text-indigo-500">Recommended actions</h3><ul className="mt-2 space-y-2 text-sm text-slate-700">{summary.data.recommended_actions.map((item) => <li key={item} className="flex gap-2"><Icon name="arrow" className="mt-0.5 h-4 w-4 shrink-0 text-indigo-500" />{item}</li>)}</ul></div></div> : null}
        </section>
        <RiskDistribution tasks={items} />
      </div>
      <div className="grid gap-6 xl:grid-cols-[1.45fr_1fr]">
        <section className="card"><div className="flex items-center justify-between"><div><h2 className="font-semibold text-slate-900">Needs attention</h2><p className="mt-1 text-xs text-slate-500">Blocked, at-risk, and overdue work.</p></div><Link to="/tasks" className="text-sm font-medium text-indigo-600 hover:underline">View tasks</Link></div>
          {tasks.isLoading || enrichment.isLoading ? <LoadingState /> : tasks.isError || enrichment.isError ? <ErrorState onRetry={() => { void tasks.refetch(); void enrichment.refetch(); }} /> : attention.length ? <div className="mt-4 divide-y divide-slate-100">{attention.map((task) => <Link key={task.id} to={`/tasks/${task.id}`} className="flex items-center gap-3 py-3.5 first:pt-0 last:pb-0"><span className={`h-2 w-2 shrink-0 rounded-full ${task.risk_status === "AT_RISK" ? "bg-amber-500" : "bg-rose-500"}`} aria-hidden="true" /><div className="min-w-0 flex-1"><p className="truncate text-sm font-semibold text-slate-800">{task.title}</p><p className="mt-1 truncate text-xs text-slate-500">{task.project_title} · {task.assignee_name ?? "Unassigned"}</p></div><PriorityBadge priority={task.priority} /><RiskPill status={task.risk_status} /><Icon name="chevron" className="h-4 w-4 rotate-90 text-slate-300" /></Link>)}</div> : <div className="mt-5 rounded-xl bg-emerald-50 p-4 text-sm text-emerald-800"><div className="flex items-center gap-2 font-medium"><Icon name="check" className="h-4 w-4" />Nothing needs immediate attention.</div><p className="mt-1 text-xs text-emerald-700">Your deterministic risk checks are clear.</p></div>}
        </section>
        <section className="card"><div className="flex items-center justify-between"><div><h2 className="font-semibold text-slate-900">Upcoming deadlines</h2><p className="mt-1 text-xs text-slate-500">Next five incomplete tasks.</p></div><Icon name="calendar" className="h-5 w-5 text-indigo-500" /></div>
          {tasks.isLoading || enrichment.isLoading ? <LoadingState /> : deadlines.length ? <div className="mt-4 space-y-1">{deadlines.map((task) => <Link key={task.id} to={`/tasks/${task.id}`} className="flex items-center gap-3 rounded-xl px-2 py-3 transition hover:bg-slate-50"><div className="flex h-9 w-9 shrink-0 flex-col items-center justify-center rounded-lg bg-indigo-50 text-indigo-700"><Icon name="calendar" className="h-4 w-4" /></div><div className="min-w-0 flex-1"><p className="truncate text-sm font-medium text-slate-800">{task.title}</p><p className="mt-0.5 truncate text-xs text-slate-500">{task.project_title}</p></div><time className={`shrink-0 text-xs font-semibold ${task.risk_status === "OVERDUE" ? "text-rose-600" : "text-slate-600"}`} dateTime={task.due_date ?? undefined}>{formatDate(task.due_date)}</time></Link>)}</div> : <p className="mt-5 rounded-xl bg-slate-50 p-4 text-sm text-slate-500">No dated open tasks. Add due dates to see the next deadlines here.</p>}
        </section>
      </div>
      <div className="grid gap-6 lg:grid-cols-2"><section className="card"><div className="flex items-center justify-between"><h2 className="font-semibold text-slate-900">Workspace projects</h2><Link to="/projects" className="text-sm font-medium text-indigo-600 hover:underline">View all</Link></div><div className="mt-4 grid gap-3 sm:grid-cols-2">{(projects.data?.items ?? []).slice(0, 4).map((project) => <Link key={project.id} to={`/tasks?project=${project.id}`} className="rounded-xl border border-slate-100 p-3 transition hover:border-indigo-200 hover:bg-indigo-50/40"><div className="flex items-center gap-2"><Icon name="projects" className="h-4 w-4 text-indigo-500" /><p className="truncate text-sm font-medium text-slate-800">{project.title}</p></div><p className="mt-2 text-xs text-slate-500">{project.status.replaceAll("_", " ")}</p></Link>)}</div>{!projects.data?.items.length && <p className="mt-4 text-sm text-slate-500">No projects yet. Create one to get started.</p>}</section><DuplicateSuggestions /></div>
      {workspaceForm && <WorkspaceForm onClose={() => setWorkspaceForm(false)} />}{projectForm && <ProjectForm onClose={() => setProjectForm(false)} />}
    </div>
  );
}
