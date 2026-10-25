import { useState, type FormEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { useAuth } from "../auth/AuthContext";
import { jsonRequest, toUserMessage } from "../lib/api";
import { useWorkspace } from "../workspace/WorkspaceContext";
import type { Workspace } from "../types";
import { Modal, inputClass, labelClass } from "./ui";
import { useToast } from "./Toast";

export function WorkspaceForm({ onClose }: { onClose: () => void }) {
  const [name, setName] = useState("");
  const { fetchWithAuth } = useAuth();
  const { refetchWorkspaces, selectWorkspace } = useWorkspace();
  const { showToast } = useToast();
  const mutation = useMutation({
    mutationFn: () => fetchWithAuth<Workspace>("/workspaces", jsonRequest("POST", { name })),
    onSuccess: async (workspace) => {
      await refetchWorkspaces();
      selectWorkspace(workspace.id);
      showToast(`Workspace “${workspace.name}” created.`);
      onClose();
    },
  });
  function submit(event: FormEvent) {
    event.preventDefault();
    mutation.mutate();
  }
  return (
    <Modal title="Create workspace" description="A separate, secure space for your team’s projects and knowledge." onClose={onClose}>
      <form onSubmit={submit} className="space-y-4">
        <label className={labelClass}>Workspace name<input required minLength={1} maxLength={120} className={inputClass} value={name} onChange={(event) => setName(event.target.value)} placeholder="e.g. Placement Prep Team" autoFocus /></label>
        {mutation.isError && <p role="alert" className="text-sm text-rose-700">{toUserMessage(mutation.error)}</p>}
        <div className="flex justify-end gap-2"><button type="button" className="btn-secondary" onClick={onClose}>Cancel</button><button className="btn-primary" disabled={mutation.isPending || !name.trim()}>{mutation.isPending ? "Creating…" : "Create workspace"}</button></div>
      </form>
    </Modal>
  );
}
