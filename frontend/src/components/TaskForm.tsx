import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "../auth/AuthContext";
import { jsonRequest, toUserMessage } from "../lib/api";
import { useWorkspace } from "../workspace/WorkspaceContext";
import type { Paginated, Project, Task, TaskPriority, TaskStatus } from "../types";
import { Modal, inputClass, labelClass } from "./ui";
import { useToast } from "./Toast";

export function TaskForm({ task, defaultProjectId, onClose, onSaved }: { task?: Task; defaultProjectId?: string; onClose: () => void; onSaved?: (task: Task) => void }) {
  const { selectedWorkspace, members } = useWorkspace();
  const { fetchWithAuth } = useAuth();
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const projectsQuery = useQuery({
    queryKey: ["projects", selectedWorkspace?.id, "all"],
    queryFn: () => fetchWithAuth<Paginated<Project>>(`/workspaces/${selectedWorkspace?.id}/projects?page_size=100`),
    enabled: Boolean(selectedWorkspace),
  });
  const [projectId, setProjectId] = useState(task?.project_id ?? defaultProjectId ?? "");
  const [title, setTitle] = useState(task?.title ?? "");
  const [description, setDescription] = useState(task?.description ?? "");
  const [status, setStatus] = useState<TaskStatus>(task?.status ?? "TODO");
  const [priority, setPriority] = useState<TaskPriority>(task?.priority ?? "MEDIUM");
  const [assigneeId, setAssigneeId] = useState(task?.assignee_id ?? "");
  const [dueDate, setDueDate] = useState(task?.due_date ?? "");
  const workspaceId = selectedWorkspace?.id;
  const mutation = useMutation({
    mutationFn: () => fetchWithAuth<Task>(
      task ? `/workspaces/${workspaceId}/tasks/${task.id}` : `/workspaces/${workspaceId}/tasks`,
      jsonRequest(task ? "PATCH" : "POST", {
        project_id: projectId,
        title,
        description,
        status,
        priority,
        assignee_id: assigneeId || null,
        due_date: dueDate || null,
      }),
    ),
    onSuccess: async (saved) => {
      await queryClient.invalidateQueries({ queryKey: ["tasks", workspaceId] });
      await queryClient.invalidateQueries({ queryKey: ["task", workspaceId, saved.id] });
      showToast(task ? "Task updated." : "Task created.");
      onSaved?.(saved);
      onClose();
    },
  });
  return (
    <Modal title={task ? "Edit task" : "Create task"} description="Assign clear ownership, priority, and deadlines." onClose={onClose} wide>
      <form onSubmit={(event) => { event.preventDefault(); mutation.mutate(); }} className="grid gap-4 sm:grid-cols-2">
        <label className={`${labelClass} sm:col-span-2`}>Project<select required className={inputClass} value={projectId} onChange={(event) => setProjectId(event.target.value)}><option value="">Select a project</option>{projectsQuery.data?.items.map((project) => <option key={project.id} value={project.id}>{project.title}</option>)}</select></label>
        <label className={`${labelClass} sm:col-span-2`}>Task title<input required maxLength={200} className={inputClass} value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Define acceptance criteria" autoFocus /></label>
        <label className={`${labelClass} sm:col-span-2`}>Description<textarea rows={4} maxLength={50000} className={inputClass} value={description} onChange={(event) => setDescription(event.target.value)} /></label>
        <label className={labelClass}>Status<select className={inputClass} value={status} onChange={(event) => setStatus(event.target.value as TaskStatus)}><option value="TODO">To do</option><option value="IN_PROGRESS">In progress</option><option value="BLOCKED">Blocked</option><option value="DONE">Done</option></select></label>
        <label className={labelClass}>Priority<select className={inputClass} value={priority} onChange={(event) => setPriority(event.target.value as TaskPriority)}><option value="LOW">Low</option><option value="MEDIUM">Medium</option><option value="HIGH">High</option><option value="CRITICAL">Critical</option></select></label>
        <label className={labelClass}>Assignee<select className={inputClass} value={assigneeId} onChange={(event) => setAssigneeId(event.target.value)}><option value="">Unassigned</option>{members.map((member) => <option key={member.user_id} value={member.user_id}>{member.full_name}</option>)}</select></label>
        <label className={labelClass}>Due date<input type="date" className={inputClass} value={dueDate} onChange={(event) => setDueDate(event.target.value)} /></label>
        {mutation.isError && <p role="alert" className="text-sm text-rose-700 sm:col-span-2">{toUserMessage(mutation.error)}</p>}
        <div className="flex justify-end gap-2 sm:col-span-2"><button type="button" className="btn-secondary" onClick={onClose}>Cancel</button><button className="btn-primary" disabled={mutation.isPending || !title.trim() || !projectId}>{mutation.isPending ? "Saving…" : task ? "Save changes" : "Create task"}</button></div>
      </form>
    </Modal>
  );
}
