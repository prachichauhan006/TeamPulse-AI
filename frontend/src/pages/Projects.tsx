import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQueries, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "../auth/AuthContext";
import { usePermissions, useWorkspace } from "../workspace/WorkspaceContext";
import type { Paginated, Project, ProjectHealth, Task } from "../types";
import { ProjectForm } from "../components/ProjectForm";
import { Icon } from "../components/Icon";
import { ConfirmDialog, EmptyState, ErrorState, LoadingState, PageHeader } from "../components/ui";
import { HealthBadge, ProjectStatusBadge } from "../components/StatusBadge";
import { formatDate, toUserMessage } from "../lib/api";
import { useToast } from "../components/Toast";

type ProjectTab = "ALL" | "ACTIVE" | "ARCHIVED";

export function Projects() {
  const { selectedWorkspace } = useWorkspace();
  const { canManage } = usePermissions();
  const { fetchWithAuth } = useAuth();
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<Project | null>(null);
  const [deleting, setDeleting] = useState<Project | null>(null);
  const [tab, setTab] = useState<ProjectTab>("ALL");
  const workspaceId = selectedWorkspace?.id;
  const query = useQuery({ queryKey: ["projects", workspaceId, "list"], queryFn: () => fetchWithAuth<Paginated<Project>>(`/workspaces/${workspaceId}/projects?page_size=100`), enabled: Boolean(workspaceId) });
  const projectItems = useMemo(() => query.data?.items ?? [], [query.data]);
  const tasksQuery = useQuery({ queryKey: ["tasks", workspaceId, "project-cards"], queryFn: () => fetchWithAuth<Paginated<Task>>(`/workspaces/${workspaceId}/tasks?page_size=100`), enabled: Boolean(workspaceId) });
  const healthQueries = useQueries({ queries: projectItems.map((project) => ({ queryKey: ["project-health", workspaceId, project.id], queryFn: () => fetchWithAuth<ProjectHealth>(`/projects/${project.id}/health`), enabled: Boolean(workspaceId) })) });
  const remove = useMutation({ mutationFn: (project: Project) => fetchWithAuth<void>(`/workspaces/${workspaceId}/projects/${project.id}`, { method: "DELETE" }), onSuccess: () => { setDeleting(null); showToast("Project deleted."); void queryClient.invalidateQueries({ queryKey: ["projects", workspaceId] }); }, onError: (error) => showToast(toUserMessage(error), "error") });
  const filtered = projectItems.filter((project) => tab === "ALL" || (tab === "ACTIVE" ? project.status === "ACTIVE" : project.status === "ARCHIVED"));
  const tabs: Array<{ value: ProjectTab; label: string }> = [{ value: "ALL", label: "All projects" }, { value: "ACTIVE", label: "Active" }, { value: "ARCHIVED", label: "Archived" }];

  return (
    <div className="space-y-6">
      <PageHeader eyebrow={selectedWorkspace?.name} title="Projects" description="A clear view of every initiative, its progress, and its health." actions={canManage && <button className="btn-primary" onClick={() => setCreating(true)}><Icon name="plus" />New project</button>} />
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-1"><div className="flex gap-1" role="tablist" aria-label="Project status filters">{tabs.map((item) => <button key={item.value} role="tab" aria-selected={tab === item.value} className={`rounded-t-xl px-4 py-2.5 text-sm font-medium transition ${tab === item.value ? "bg-white text-indigo-700 shadow-sm ring-1 ring-slate-200" : "text-slate-500 hover:bg-white/60 hover:text-slate-800"}`} onClick={() => setTab(item.value)}>{item.label}<span className="ml-2 text-xs text-slate-400">{item.value === "ALL" ? projectItems.length : projectItems.filter((project) => item.value === "ACTIVE" ? project.status === "ACTIVE" : project.status === "ARCHIVED").length}</span></button>)}</div><span className="text-xs text-slate-400">Health is calculated from live task data</span></div>
      {query.isLoading ? <LoadingState /> : query.isError ? <ErrorState onRetry={() => void query.refetch()} /> : !filtered.length ? <EmptyState title={projectItems.length ? "No projects in this view" : "No projects yet"} description={projectItems.length ? "Try another status tab to find your project." : "Start with a project, or let AI draft a structured plan for your approval."} action={canManage && !projectItems.length && <button className="btn-primary" onClick={() => setCreating(true)}>Create project</button>} /> : <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">{filtered.map((project, index) => {
        const projectTasks = (tasksQuery.data?.items ?? []).filter((task) => task.project_id === project.id);
        const complete = projectTasks.filter((task) => task.status === "DONE").length;
        const progress = projectTasks.length ? Math.round((complete / projectTasks.length) * 100) : 0;
        const deadline = projectTasks.filter((task) => task.status !== "DONE" && task.due_date).sort((a, b) => (a.due_date ?? "").localeCompare(b.due_date ?? ""))[0]?.due_date;
        const healthQuery = healthQueries[projectItems.findIndex((item) => item.id === project.id) ?? index];
        return <article key={project.id} className="card flex min-h-[19rem] flex-col p-5 transition hover:-translate-y-0.5 hover:border-indigo-200 hover:shadow-lg hover:shadow-indigo-100/40"><div className="flex items-start justify-between gap-3"><div className="rounded-xl bg-indigo-50 p-2.5 text-indigo-600"><Icon name="projects" className="h-5 w-5" /></div><div className="flex items-center gap-1"><ProjectStatusBadge status={project.status} />{canManage && <><button className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-indigo-600" onClick={() => setEditing(project)} aria-label={`Edit ${project.title}`}><Icon name="edit" className="h-4 w-4" /></button><button className="rounded-lg p-2 text-slate-400 hover:bg-rose-50 hover:text-rose-600" onClick={() => setDeleting(project)} aria-label={`Delete ${project.title}`}><Icon name="trash" className="h-4 w-4" /></button></>}</div></div><h2 className="mt-4 text-lg font-semibold text-slate-900">{project.title}</h2><p className="mt-2 line-clamp-2 flex-1 text-sm leading-6 text-slate-500">{project.description || "No description yet."}</p><div className="mt-4 flex items-center justify-between gap-2">{healthQuery?.data ? <HealthBadge health={healthQuery.data.health} /> : healthQuery?.isError ? <span className="text-xs text-amber-700">Health unavailable</span> : <span className="text-xs text-slate-400">Checking health…</span>}<span className="text-xs text-slate-500">{complete}/{projectTasks.length} done</span></div><div className="mt-3"><div className="flex items-center justify-between text-xs"><span className="text-slate-500">Progress</span><strong className="text-slate-800">{progress}%</strong></div><div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-100" role="progressbar" aria-label={`${project.title} progress`} aria-valuenow={progress} aria-valuemin={0} aria-valuemax={100}><div className="h-full rounded-full bg-indigo-600 transition-all" style={{ width: `${progress}%` }} /></div></div><div className="mt-4 flex items-center justify-between border-t border-slate-100 pt-3 text-xs text-slate-500"><span className="flex items-center gap-1.5"><Icon name="calendar" className="h-3.5 w-3.5" />{deadline ? `Next ${formatDate(deadline)}` : "No open deadline"}</span><Link to={`/tasks?project=${project.id}`} className="font-semibold text-indigo-600 hover:underline">View tasks <span aria-hidden="true">→</span></Link></div></article>;
      })}</div>}
      {creating && <ProjectForm onClose={() => setCreating(false)} />}{editing && <ProjectForm project={editing} onClose={() => setEditing(null)} />}<ConfirmDialog open={Boolean(deleting)} title={`Delete ${deleting?.title ?? "project"}?`} description="Only an empty project can be deleted. Move or delete its active tasks first; the backend enforces this safeguard." destructive confirmLabel="Delete project" busy={remove.isPending} onCancel={() => setDeleting(null)} onConfirm={() => deleting && remove.mutate(deleting)} />
    </div>
  );
}
