import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "../auth/AuthContext";
import { usePermissions, useWorkspace } from "../workspace/WorkspaceContext";
import { useTaskViews } from "../hooks/useTaskViews";
import type { Paginated, Task, TaskDependency } from "../types";
import { RiskBadge } from "../components/RiskBadge";
import { TaskForm } from "../components/TaskForm";
import { Icon } from "../components/Icon";
import { ConfirmDialog, EmptyState, ErrorState, LoadingState, PageHeader, inputClass } from "../components/ui";
import { formatDate, jsonRequest, toUserMessage } from "../lib/api";
import { useToast } from "../components/Toast";

export function TaskDetail() {
  const { taskId } = useParams();
  const { selectedWorkspace } = useWorkspace();
  const { canEdit, canManage } = usePermissions();
  const { fetchWithAuth } = useAuth();
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const navigate = useNavigate();
  const [editing, setEditing] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [dependencyId, setDependencyId] = useState("");
  const workspaceId = selectedWorkspace?.id;
  const taskQuery = useQuery({ queryKey: ["task", workspaceId, taskId], queryFn: () => fetchWithAuth<Task>(`/workspaces/${workspaceId}/tasks/${taskId}`), enabled: Boolean(workspaceId && taskId) });
  const allTasks = useQuery({ queryKey: ["tasks", workspaceId, "dependencies"], queryFn: () => fetchWithAuth<Paginated<Task>>(`/workspaces/${workspaceId}/tasks?page_size=100`), enabled: Boolean(workspaceId) });
  const enrichment = useTaskViews(taskQuery.data ? [taskQuery.data] : []);
  const task = enrichment.views[0];
  const invalidate = () => Promise.all([queryClient.invalidateQueries({ queryKey: ["task", workspaceId, taskId] }), queryClient.invalidateQueries({ queryKey: ["tasks", workspaceId] }), queryClient.invalidateQueries({ queryKey: ["task-enrichment", workspaceId, taskId] })]);
  const dependencyMutation = useMutation({ mutationFn: () => fetchWithAuth<TaskDependency>(`/workspaces/${workspaceId}/tasks/${taskId}/dependencies`, jsonRequest("POST", { depends_on_task_id: dependencyId })), onSuccess: async () => { await invalidate(); setDependencyId(""); showToast("Dependency added and risks recalculated."); }, onError: (error) => showToast(toUserMessage(error), "error") });
  const removeDependency = useMutation({ mutationFn: (dependsOnId: string) => fetchWithAuth<void>(`/workspaces/${workspaceId}/tasks/${taskId}/dependencies/${dependsOnId}`, { method: "DELETE" }), onSuccess: async () => { await invalidate(); showToast("Dependency removed and risks recalculated."); }, onError: (error) => showToast(toUserMessage(error), "error") });
  const deleteMutation = useMutation({ mutationFn: () => fetchWithAuth<void>(`/workspaces/${workspaceId}/tasks/${taskId}`, { method: "DELETE" }), onSuccess: () => { showToast("Task deleted."); void queryClient.invalidateQueries({ queryKey: ["tasks", workspaceId] }); navigate("/tasks"); }, onError: (error) => showToast(toUserMessage(error), "error") });

  if (taskQuery.isLoading) return <LoadingState />;
  if (taskQuery.isError) return <ErrorState message="This task could not be loaded or you don’t have access to it." onRetry={() => void taskQuery.refetch()} />;
  if (!task) return null;
  const candidates = (allTasks.data?.items ?? []).filter((item) => item.id !== task.id && !task.dependency_ids.includes(item.id));
  return (
    <div className="space-y-6">
      <Link to="/tasks" className="inline-flex items-center gap-2 text-sm font-medium text-slate-500 hover:text-indigo-600">← Back to tasks</Link>
      <PageHeader title={task.title} description={`Created ${formatDate(task.created_at)} · Version ${task.version}`} actions={<div className="flex gap-2">{canEdit && <button className="btn-secondary" onClick={() => setEditing(true)}><Icon name="edit" />Edit</button>}{canManage && <button className="btn-danger" onClick={() => setDeleting(true)}><Icon name="trash" />Delete</button>}</div>} />
      <div className="grid gap-6 lg:grid-cols-[1.5fr_1fr]"><div className="space-y-6"><section className="card"><h2 className="font-semibold">Description</h2><p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-slate-600">{task.description || "No description provided."}</p></section>
        <section className="card"><div><h2 className="font-semibold">Dependencies</h2><p className="mt-1 text-sm text-slate-500">This task can finish only after every dependency is done. Cycles are rejected.</p></div><div className="mt-4 space-y-2">{task.dependency_ids.length ? task.dependency_ids.map((id) => { const dependency = allTasks.data?.items.find((item) => item.id === id); return <div key={id} className="flex items-center gap-3 rounded-xl bg-slate-50 p-3"><div className="flex-1"><Link className="text-sm font-medium text-slate-800 hover:text-indigo-600" to={`/tasks/${id}`}>{dependency?.title ?? "Task in this workspace"}</Link>{dependency && <p className="text-xs text-slate-500">{dependency.status.replaceAll("_", " ")}</p>}</div>{canEdit && <button className="rounded-lg p-2 text-slate-400 hover:bg-rose-50 hover:text-rose-600" aria-label={`Remove dependency ${dependency?.title ?? id}`} onClick={() => removeDependency.mutate(id)}><Icon name="close" className="h-4 w-4" /></button>}</div>; }) : <EmptyState title="No dependencies" description="This task has no upstream blockers." />}</div>{canEdit && <form className="mt-4 flex flex-col gap-2 sm:flex-row" onSubmit={(event) => { event.preventDefault(); dependencyMutation.mutate(); }}><label className="sr-only" htmlFor="dependency">Add dependency</label><select id="dependency" required className={inputClass} value={dependencyId} onChange={(event) => setDependencyId(event.target.value)}><option value="">Select an upstream task…</option>{candidates.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}</select><button className="btn-secondary shrink-0" disabled={!dependencyId || dependencyMutation.isPending}>{dependencyMutation.isPending ? "Adding…" : "Add dependency"}</button></form>}</section>
      </div><aside className="space-y-6"><section className="card"><h2 className="font-semibold">Task health</h2><div className="mt-4">{enrichment.isLoading ? <LoadingState label="Calculating risk…" /> : enrichment.isError ? <ErrorState message="Risk details are unavailable." onRetry={() => void enrichment.refetch()} /> : <RiskBadge status={task.risk_status} reasons={task.risk_reasons} showReason />}</div></section><section className="card space-y-4 text-sm"><div><p className="text-xs uppercase tracking-wide text-slate-400">Status</p><p className="mt-1 font-medium">{task.status.replaceAll("_", " ")}</p></div><div><p className="text-xs uppercase tracking-wide text-slate-400">Priority</p><p className="mt-1 font-medium">{task.priority}</p></div><div><p className="text-xs uppercase tracking-wide text-slate-400">Assignee</p><p className="mt-1 font-medium">{task.assignee_name ?? "Unassigned"}</p></div><div><p className="text-xs uppercase tracking-wide text-slate-400">Due date</p><p className="mt-1 font-medium">{formatDate(task.due_date)}</p></div><div><p className="text-xs uppercase tracking-wide text-slate-400">Last updated</p><p className="mt-1 font-medium">{formatDate(task.updated_at)}</p></div></section></aside></div>
      {editing && <TaskForm task={task} onClose={() => setEditing(false)} />}<ConfirmDialog open={deleting} title="Delete this task?" description="The task and its dependency links will be permanently removed from active views. This action is recorded in the audit log." confirmLabel="Delete task" destructive busy={deleteMutation.isPending} onCancel={() => setDeleting(false)} onConfirm={() => deleteMutation.mutate()} />
    </div>
  );
}
