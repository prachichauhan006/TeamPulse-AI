import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "../auth/AuthContext";
import { jsonRequest, toUserMessage } from "../lib/api";
import { useWorkspace } from "../workspace/WorkspaceContext";
import type { Project, ProjectStatus } from "../types";
import { Modal, inputClass, labelClass } from "./ui";
import { useToast } from "./Toast";

export function ProjectForm({ project, onClose, onSaved }: { project?: Project; onClose: () => void; onSaved?: (project: Project) => void }) {
  const { selectedWorkspace } = useWorkspace();
  const { fetchWithAuth } = useAuth();
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const [title, setTitle] = useState(project?.title ?? "");
  const [description, setDescription] = useState(project?.description ?? "");
  const [status, setStatus] = useState<ProjectStatus>(project?.status ?? "ACTIVE");
  const mutation = useMutation({
    mutationFn: () => fetchWithAuth<Project>(project ? `/workspaces/${selectedWorkspace?.id}/projects/${project.id}` : `/workspaces/${selectedWorkspace?.id}/projects`, jsonRequest(project ? "PATCH" : "POST", { title, description, status })),
    onSuccess: async (saved) => { await queryClient.invalidateQueries({ queryKey: ["projects", selectedWorkspace?.id] }); showToast(project ? "Project updated." : `Project “${saved.title}” created.`); onSaved?.(saved); onClose(); },
  });
  return <Modal title={project ? "Edit project" : "Create project"} description={`in ${selectedWorkspace?.name ?? "workspace"}`} onClose={onClose}><form onSubmit={(event) => { event.preventDefault(); mutation.mutate(); }} className="space-y-4"><label className={labelClass}>Project title<input required maxLength={160} className={inputClass} value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Placement Preparation Platform" autoFocus /></label><label className={labelClass}>Description<textarea rows={4} maxLength={20000} className={inputClass} value={description} onChange={(event) => setDescription(event.target.value)} placeholder="What does success look like?" /></label><label className={labelClass}>Status<select className={inputClass} value={status} onChange={(event) => setStatus(event.target.value as ProjectStatus)}><option value="ACTIVE">Active</option><option value="ON_HOLD">On hold</option><option value="COMPLETED">Completed</option><option value="ARCHIVED">Archived</option></select></label>{mutation.isError && <p role="alert" className="text-sm text-rose-700">{toUserMessage(mutation.error)}</p>}<div className="flex justify-end gap-2"><button type="button" className="btn-secondary" onClick={onClose}>Cancel</button><button className="btn-primary" disabled={mutation.isPending || !title.trim()}>{mutation.isPending ? "Saving…" : project ? "Save changes" : "Create project"}</button></div></form></Modal>;
}
