import { useMemo, useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "../auth/AuthContext";
import { usePermissions, useWorkspace } from "../workspace/WorkspaceContext";
import type { Paginated, Project, Task, TaskPriority, TaskStatus, TaskView, WorkspaceMember } from "../types";
import { formatDate, toUserMessage } from "../lib/api";
import { EmptyState, ErrorState, LoadingState, Modal, PageHeader, inputClass, labelClass } from "../components/ui";
import { Icon } from "../components/Icon";
import { PriorityBadge, RiskPill, TaskStatusBadge } from "../components/StatusBadge";
import { KanbanBoard } from "../components/KanbanBoard";
import { useToast } from "../components/Toast";
import { useTaskViews } from "../hooks/useTaskViews";

const statusOptions: Array<{ value: TaskStatus; label: string }> = [{ value: "TODO", label: "To Do" }, { value: "IN_PROGRESS", label: "In Progress" }, { value: "BLOCKED", label: "Blocked" }, { value: "DONE", label: "Done" }];

export function Tasks() {
  const { selectedWorkspace, members } = useWorkspace();
  const { canEdit } = usePermissions();
  const { fetchWithAuth } = useAuth();
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const workspaceId = selectedWorkspace?.id;
  const [searchParams] = useSearchParams();
  const [view, setView] = useState<"list" | "kanban">("list");
  const [showForm, setShowForm] = useState(false);
  const [search, setSearch] = useState("");
  const [project, setProject] = useState(searchParams.get("project") ?? "");
  const [status, setStatus] = useState("");
  const [priority, setPriority] = useState("");
  const [risk, setRisk] = useState("");
  const [assignee, setAssignee] = useState("");
  const [statusOverrides, setStatusOverrides] = useState<Record<string, TaskStatus>>({});
  const projectsQuery = useQuery({ queryKey: ["projects", workspaceId], queryFn: () => fetchWithAuth<{ items: Project[] }>(`/workspaces/${workspaceId}/projects?page_size=100`), enabled: Boolean(workspaceId) });
  const tasksQuery = useQuery({ queryKey: ["tasks", workspaceId], queryFn: () => fetchWithAuth<Paginated<Task>>(`/workspaces/${workspaceId}/tasks?page_size=100`), enabled: Boolean(workspaceId) });
  const projects = useMemo(() => projectsQuery.data?.items ?? [], [projectsQuery.data]);
  const baseViews = useTaskViews(tasksQuery.data?.items ?? [], projects);
  const views = useMemo(() => baseViews.views.map((task) => statusOverrides[task.id] ? { ...task, status: statusOverrides[task.id] } : task), [baseViews.views, statusOverrides]);

  const statusMutation = useMutation({
    mutationFn: async ({ task, nextStatus }: { task: TaskView; nextStatus: TaskStatus }) => {
      await fetchWithAuth<Task>(`/workspaces/${workspaceId}/tasks/${task.id}`, { method: "PATCH", body: JSON.stringify({ status: nextStatus }) });
      return { task, nextStatus };
    },
    onMutate: ({ task, nextStatus }) => {
      const previousStatus = task.status;
      setStatusOverrides((current) => ({ ...current, [task.id]: nextStatus }));
      return { previousStatus };
    },
    onError: (error, { task }, context) => {
      setStatusOverrides((current) => ({ ...current, [task.id]: context?.previousStatus ?? task.status }));
      showToast(`${toUserMessage(error)} The task was restored to its previous status.`, "error");
    },
    onSuccess: ({ nextStatus }) => showToast(`Task moved to ${statusOptions.find((option) => option.value === nextStatus)?.label ?? nextStatus}.`),
    onSettled: async (_data, _error, { task }) => {
      // Invalidate every dependent risk view, not only the moved task. A BLOCKED
      // transition can change downstream task risk without changing its version.
      try {
        await Promise.all([
          queryClient.invalidateQueries({ queryKey: ["tasks", workspaceId] }),
          queryClient.invalidateQueries({ queryKey: ["task", workspaceId, task.id] }),
          queryClient.invalidateQueries({ queryKey: ["task-enrichment", workspaceId] }),
          queryClient.invalidateQueries({ queryKey: ["projects", workspaceId] }),
          queryClient.invalidateQueries({ queryKey: ["project-health", workspaceId] }),
          queryClient.invalidateQueries({ queryKey: ["weekly-summary", workspaceId] }),
        ]);
      } finally {
        setStatusOverrides((current) => {
          const next = { ...current };
          delete next[task.id];
          return next;
        });
      }
    },
  });

  const create = useMutation({
    mutationFn: (body: Record<string, unknown>) => fetchWithAuth<Task>(`/workspaces/${workspaceId}/tasks`, { method: "POST", body: JSON.stringify(body) }),
    onSuccess: () => { showToast("Task created."); setShowForm(false); void queryClient.invalidateQueries({ queryKey: ["tasks", workspaceId] }); void queryClient.invalidateQueries({ queryKey: ["projects", workspaceId] }); },
    onError: (error) => showToast(toUserMessage(error), "error"),
  });
  function changeStatus(task: TaskView, nextStatus: TaskStatus) {
    if (!canEdit || task.status === nextStatus || statusMutation.isPending) return;
    statusMutation.mutate({ task, nextStatus });
  }

  const filtered = views.filter((task) => {
    const query = search.trim().toLowerCase();
    return (!query || `${task.title} ${task.description}`.toLowerCase().includes(query)) && (!project || task.project_id === project) && (!status || task.status === status) && (!priority || task.priority === priority) && (!risk || task.risk_status === risk) && (!assignee || (assignee === "unassigned" ? !task.assignee_id : task.assignee_id === assignee));
  });
  const isLoading = tasksQuery.isLoading || projectsQuery.isLoading || baseViews.isLoading;
  const hasFilters = Boolean(search || project || status || priority || risk || assignee);

  return (
    <div>
      <PageHeader eyebrow={selectedWorkspace?.name} title="Tasks" description="Plan the work, make dependencies visible, and keep every status change accountable." actions={canEdit && <button className="btn-primary" onClick={() => setShowForm(true)}><Icon name="plus" />New task</button>} />
      <section className="card mb-5 p-4" aria-label="Task filters">
        <div className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-400"><Icon name="filter" className="h-4 w-4" />Filter workspace work{hasFilters && <button className="ml-auto normal-case tracking-normal text-indigo-600 hover:underline" onClick={() => { setSearch(""); setProject(""); setStatus(""); setPriority(""); setRisk(""); setAssignee(""); }}>Clear filters</button>}</div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
          <label className="text-xs font-medium text-slate-600 sm:col-span-2 lg:col-span-1">Search tasks<input aria-label="Search tasks" className={inputClass} value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Title or description" /></label>
          <label className="text-xs font-medium text-slate-600">Project<select aria-label="Filter by project" className={inputClass} value={project} onChange={(event) => setProject(event.target.value)}><option value="">All projects</option>{projects.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}</select></label>
          <label className="text-xs font-medium text-slate-600">Status<select aria-label="Filter by status" className={inputClass} value={status} onChange={(event) => setStatus(event.target.value)}><option value="">All statuses</option>{statusOptions.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
          <label className="text-xs font-medium text-slate-600">Priority<select aria-label="Filter by priority" className={inputClass} value={priority} onChange={(event) => setPriority(event.target.value)}><option value="">All priorities</option>{["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((item) => <option key={item}>{item}</option>)}</select></label>
          <label className="text-xs font-medium text-slate-600">Risk<select aria-label="Filter by risk" className={inputClass} value={risk} onChange={(event) => setRisk(event.target.value)}><option value="">All risk states</option><option value="ON_TRACK">On track</option><option value="AT_RISK">At risk</option><option value="OVERDUE">Overdue</option><option value="BLOCKED">Blocked</option></select></label>
          <label className="text-xs font-medium text-slate-600">Assignee<select aria-label="Filter by assignee" className={inputClass} value={assignee} onChange={(event) => setAssignee(event.target.value)}><option value="">All assignees</option><option value="unassigned">Unassigned</option>{members.map((member) => <option key={member.user_id} value={member.user_id}>{member.full_name}</option>)}</select></label>
        </div>
      </section>
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3"><p className="text-sm text-slate-500"><strong className="text-slate-800">{filtered.length}</strong> of {views.length} tasks shown{statusMutation.isPending && <span className="ml-2 text-indigo-600" role="status">Saving status…</span>}</p><div className="flex rounded-xl border border-slate-200 bg-white p-1" role="group" aria-label="Task view"><button aria-pressed={view === "list"} className={`rounded-lg px-3.5 py-2 text-sm font-medium transition ${view === "list" ? "bg-indigo-600 text-white shadow-sm" : "text-slate-500 hover:bg-slate-50"}`} onClick={() => setView("list")}>List</button><button aria-pressed={view === "kanban"} className={`rounded-lg px-3.5 py-2 text-sm font-medium transition ${view === "kanban" ? "bg-indigo-600 text-white shadow-sm" : "text-slate-500 hover:bg-slate-50"}`} onClick={() => setView("kanban")}>Kanban</button></div></div>
      {isLoading ? <LoadingState label="Loading tasks, dependencies, and risk…" /> : tasksQuery.isError ? <ErrorState onRetry={() => void tasksQuery.refetch()} /> : !filtered.length ? <EmptyState title={views.length ? "No tasks match these filters" : "No tasks yet"} description={views.length ? "Try clearing a filter or searching with a different phrase." : "Create the first task to start building your team’s execution plan."} action={canEdit && !views.length && <button className="btn-primary" onClick={() => setShowForm(true)}>Create task</button>} /> : view === "kanban" ? <KanbanBoard tasks={filtered} canEdit={canEdit && !statusMutation.isPending} onStatusChange={changeStatus} /> : <div className="card overflow-hidden p-0"><div className="overflow-x-auto"><table className="w-full min-w-[960px] text-left text-sm"><thead className="bg-slate-50/80 text-xs uppercase tracking-wider text-slate-400"><tr><th className="px-5 py-3.5 font-semibold">Task</th><th className="px-4 py-3.5 font-semibold">Project</th><th className="px-4 py-3.5 font-semibold">Status</th><th className="px-4 py-3.5 font-semibold">Priority</th><th className="px-4 py-3.5 font-semibold">Assignee</th><th className="px-4 py-3.5 font-semibold">Due date</th><th className="px-4 py-3.5 font-semibold">Risk</th></tr></thead><tbody className="divide-y divide-slate-100">{filtered.map((task) => <tr key={task.id} className="transition hover:bg-indigo-50/30"><td className="px-5 py-4"><Link className="font-semibold text-slate-900 hover:text-indigo-700" to={`/tasks/${task.id}`}>{task.title}</Link>{task.dependency_ids.length > 0 && <span className="ml-2 text-xs text-slate-400">↳ {task.dependency_ids.length}</span>}</td><td className="max-w-36 truncate px-4 py-4 text-slate-500">{task.project_title}</td><td className="px-4 py-4">{canEdit ? <select aria-label={`Status for ${task.title}`} className="rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-xs text-slate-700 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100" value={task.status} disabled={statusMutation.isPending} onChange={(event) => changeStatus(task, event.target.value as TaskStatus)}>{statusOptions.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select> : <TaskStatusBadge status={task.status} />}</td><td className="px-4 py-4"><PriorityBadge priority={task.priority} /></td><td className="px-4 py-4 text-slate-600">{task.assignee_name ?? "Unassigned"}</td><td className="whitespace-nowrap px-4 py-4 text-slate-500">{formatDate(task.due_date)}</td><td className="px-4 py-4"><RiskPill status={task.risk_status} />{task.risk_status === "ON_TRACK" && <span className="text-xs text-slate-400">On track</span>}</td></tr>)}</tbody></table></div></div>}
      {baseViews.isError && <p className="mt-3 text-xs text-amber-700" role="status">Some risk details could not be refreshed. Status changes remain available; try reloading for the latest dependency information.</p>}
      {showForm && <TaskForm projects={projects} members={members} onClose={() => setShowForm(false)} onSubmit={(body) => create.mutate(body)} busy={create.isPending} />}
    </div>
  );
}

export function TaskForm({ task, projects, members, onClose, onSubmit, busy }: { task?: TaskView; projects: Project[]; members: WorkspaceMember[]; onClose: () => void; onSubmit: (body: Record<string, unknown>) => void; busy: boolean }) {
  const [title, setTitle] = useState(task?.title ?? "");
  const [description, setDescription] = useState(task?.description ?? "");
  const [projectId, setProjectId] = useState(task?.project_id ?? projects[0]?.id ?? "");
  const [status, setStatus] = useState<TaskStatus>(task?.status ?? "TODO");
  const [priority, setPriority] = useState<TaskPriority>(task?.priority ?? "MEDIUM");
  const [assigneeId, setAssigneeId] = useState(task?.assignee_id ?? "");
  const [dueDate, setDueDate] = useState(task?.due_date ?? "");
  const [error, setError] = useState("");
  function submit(event: FormEvent) {
    event.preventDefault();
    if (!projectId) { setError("Create a project before adding a task."); return; }
    onSubmit({ project_id: projectId, title, description, status, priority, assignee_id: assigneeId || null, due_date: dueDate || null });
  }
  return <Modal title={task ? "Edit task" : "Create a task"} description="Keep ownership, priority, and timing clear. Dependencies are managed from task detail." onClose={onClose}><form className="space-y-4" onSubmit={submit}><label className={labelClass}>Task title<input required maxLength={200} className={inputClass} value={title} onChange={(event) => setTitle(event.target.value)} /></label><label className={labelClass}>Description<textarea rows={4} className={inputClass} value={description} onChange={(event) => setDescription(event.target.value)} /></label><label className={labelClass}>Project<select required className={inputClass} value={projectId} onChange={(event) => setProjectId(event.target.value)}><option value="">Select a project</option>{projects.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}</select></label><div className="grid grid-cols-2 gap-3"><label className={labelClass}>Status<select className={inputClass} value={status} onChange={(event) => setStatus(event.target.value as TaskStatus)}>{statusOptions.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label><label className={labelClass}>Priority<select className={inputClass} value={priority} onChange={(event) => setPriority(event.target.value as TaskPriority)}>{["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((item) => <option key={item}>{item}</option>)}</select></label></div><label className={labelClass}>Assignee<select className={inputClass} value={assigneeId} onChange={(event) => setAssigneeId(event.target.value)}><option value="">Unassigned</option>{members.map((member) => <option key={member.user_id} value={member.user_id}>{member.full_name}</option>)}</select></label><label className={labelClass}>Due date<input type="date" className={inputClass} value={dueDate} onChange={(event) => setDueDate(event.target.value)} /></label>{error && <p role="alert" className="text-sm text-rose-600">{error}</p>}<div className="flex justify-end gap-2"><button type="button" className="btn-secondary" onClick={onClose}>Cancel</button><button className="btn-primary" disabled={busy}>{busy ? "Saving…" : task ? "Save changes" : "Create task"}</button></div></form></Modal>;
}


