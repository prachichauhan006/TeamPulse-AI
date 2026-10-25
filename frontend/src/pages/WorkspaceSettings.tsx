import { useEffect, useState, type FormEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "../auth/AuthContext";
import { RoleGate, usePermissions, useWorkspace } from "../workspace/WorkspaceContext";
import type { Workspace, WorkspaceMember, WorkspaceRole } from "../types";
import { WorkspaceForm } from "../components/WorkspaceForm";
import { Icon } from "../components/Icon";
import { Badge, ConfirmDialog, PageHeader, inputClass, labelClass } from "../components/ui";
import { jsonRequest, toUserMessage } from "../lib/api";
import { useToast } from "../components/Toast";

export function WorkspaceSettings() {
  const { selectedWorkspace, members, refetchMembers, refetchWorkspaces, selectWorkspace } = useWorkspace();
  const { isOwner, canManage } = usePermissions();
  const { fetchWithAuth, user } = useAuth();
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const [creating, setCreating] = useState(false);
  const [workspaceName, setWorkspaceName] = useState(selectedWorkspace?.name ?? "");
  const [deletingWorkspace, setDeletingWorkspace] = useState(false);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<Exclude<WorkspaceRole, "OWNER">>("MEMBER");
  const [removeMember, setRemoveMember] = useState<WorkspaceMember | null>(null);
  const workspaceId = selectedWorkspace?.id;
  useEffect(() => setWorkspaceName(selectedWorkspace?.name ?? ""), [selectedWorkspace?.id, selectedWorkspace?.name]);
  const renameWorkspace = useMutation({ mutationFn: () => fetchWithAuth<Workspace>(`/workspaces/${workspaceId}`, jsonRequest("PATCH", { name: workspaceName })), onSuccess: async () => { await refetchWorkspaces(); showToast("Workspace name updated."); }, onError: (error) => showToast(toUserMessage(error), "error") });
  const deleteWorkspace = useMutation({ mutationFn: () => fetchWithAuth<void>(`/workspaces/${workspaceId}`, jsonRequest("DELETE", { confirmation: selectedWorkspace?.name ?? "" })), onSuccess: async () => { setDeletingWorkspace(false); selectWorkspace(""); await refetchWorkspaces(); showToast("Workspace deleted."); }, onError: (error) => showToast(toUserMessage(error), "error") });
  const invite = useMutation({ mutationFn: () => fetchWithAuth<WorkspaceMember>(`/workspaces/${workspaceId}/members`, jsonRequest("POST", { email, role })), onSuccess: async (member) => { await refetchMembers(); setEmail(""); showToast(`${member.full_name} added to the workspace.`); }, onError: (error) => showToast(toUserMessage(error), "error") });
  const updateRole = useMutation({ mutationFn: ({ member, nextRole }: { member: WorkspaceMember; nextRole: WorkspaceRole }) => fetchWithAuth<WorkspaceMember>(`/workspaces/${workspaceId}/members/${member.user_id}`, jsonRequest("PATCH", { role: nextRole })), onSuccess: async () => { await refetchMembers(); showToast("Member role updated."); }, onError: (error) => showToast(toUserMessage(error), "error") });
  const remove = useMutation({ mutationFn: (member: WorkspaceMember) => fetchWithAuth<void>(`/workspaces/${workspaceId}/members/${member.user_id}`, { method: "DELETE" }), onSuccess: async () => { await refetchMembers(); await queryClient.invalidateQueries({ queryKey: ["tasks", workspaceId] }); setRemoveMember(null); showToast("Member removed from the workspace."); }, onError: (error) => showToast(toUserMessage(error), "error") });
  return (
    <div className="space-y-6">
      <PageHeader title="Workspace & Team" description="Manage membership and role-based access. Every data query remains workspace-scoped." actions={<button className="btn-secondary" onClick={() => setCreating(true)}><Icon name="plus" />New workspace</button>} />
      {canManage && <section className="card"><div className="flex flex-col gap-4 md:flex-row md:items-end"><form className="flex flex-1 flex-col gap-3 sm:flex-row sm:items-end" onSubmit={(event) => { event.preventDefault(); renameWorkspace.mutate(); }}><label className={`${labelClass} flex-1`}>Workspace name<input required maxLength={120} className={inputClass} value={workspaceName} onChange={(event) => setWorkspaceName(event.target.value)} /></label><button className="btn-secondary" disabled={renameWorkspace.isPending || !workspaceName.trim() || workspaceName === selectedWorkspace?.name}>{renameWorkspace.isPending ? "Saving…" : "Rename workspace"}</button></form>{isOwner && <button className="btn-danger" onClick={() => setDeletingWorkspace(true)}><Icon name="trash" />Delete workspace</button>}</div></section>}
      <div className="grid gap-6 xl:grid-cols-[1fr_0.65fr]">
        <section className="card overflow-hidden p-0"><div className="border-b border-slate-100 p-5"><h2 className="font-semibold">Members of {selectedWorkspace?.name}</h2><p className="mt-1 text-sm text-slate-500">{members.length} people with access</p></div><div className="divide-y divide-slate-100">{members.map((member) => <div key={member.user_id} className="flex flex-col gap-3 p-5 sm:flex-row sm:items-center"><div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-indigo-100 font-semibold text-indigo-700">{member.full_name.slice(0, 1).toUpperCase()}</div><div className="min-w-0 flex-1"><p className="truncate font-medium text-slate-900">{member.full_name}{member.user_id === user?.id && <span className="ml-2 text-xs font-normal text-slate-400">You</span>}</p><p className="truncate text-sm text-slate-500">{member.email}</p></div><RoleGate permission="manage" fallback={<Badge tone="indigo">{member.role}</Badge>}><div className="flex items-center gap-2"><select aria-label={`Role for ${member.full_name}`} className="rounded-xl border-slate-200 py-2 text-sm" value={member.role} disabled={member.role === "OWNER" || !isOwner && member.user_id === user?.id} onChange={(event) => updateRole.mutate({ member, nextRole: event.target.value as WorkspaceRole })}><option value="OWNER" disabled>Owner</option><option value="ADMIN">Admin</option><option value="MEMBER">Member</option><option value="VIEWER">Viewer</option></select>{member.role !== "OWNER" && <button className="rounded-lg p-2 text-slate-400 hover:bg-rose-50 hover:text-rose-600" onClick={() => setRemoveMember(member)} aria-label={`Remove ${member.full_name}`}><Icon name="trash" className="h-4 w-4" /></button>}</div></RoleGate></div>)}</div></section>
        <div className="space-y-6">
          <RoleGate permission="manage" fallback={<section className="card"><h2 className="font-semibold">Your access</h2><p className="mt-2 text-sm leading-6 text-slate-600">Member administration is limited to workspace owners and admins. Your task and document permissions are unchanged.</p></section>}>
            <section className="card"><h2 className="font-semibold">Add a team member</h2><p className="mt-1 text-sm text-slate-500">They must already have a TeamPulse account.</p><form className="mt-4 space-y-4" onSubmit={(event: FormEvent) => { event.preventDefault(); invite.mutate(); }}><label className={labelClass}>Email address<input type="email" required className={inputClass} value={email} onChange={(event) => setEmail(event.target.value)} placeholder="teammate@example.com" /></label><label className={labelClass}>Role<select className={inputClass} value={role} onChange={(event) => setRole(event.target.value as Exclude<WorkspaceRole, "OWNER">)}><option value="MEMBER">Member — create and edit work</option><option value="VIEWER">Viewer — read only</option>{isOwner && <option value="ADMIN">Admin — manage members</option>}</select></label>{invite.isError && <p role="alert" className="text-sm text-rose-700">{toUserMessage(invite.error)}</p>}<button className="btn-primary w-full" disabled={invite.isPending || !email}>{invite.isPending ? "Adding…" : "Add to workspace"}</button></form></section>
          </RoleGate>
          <section className="card"><h2 className="font-semibold">Role guide</h2><dl className="mt-4 space-y-3 text-sm"><div><dt className="font-medium">Owner</dt><dd className="text-slate-500">Full control and ownership safeguards.</dd></div><div><dt className="font-medium">Admin</dt><dd className="text-slate-500">Manage work, members, AI, and audit.</dd></div><div><dt className="font-medium">Member</dt><dd className="text-slate-500">Create and edit tasks, notes, and documents.</dd></div><div><dt className="font-medium">Viewer</dt><dd className="text-slate-500">Read workspace data without changes.</dd></div></dl></section>
        </div>
      </div>
      {creating && <WorkspaceForm onClose={() => setCreating(false)} />}
      <ConfirmDialog open={Boolean(removeMember)} title={`Remove ${removeMember?.full_name ?? "member"}?`} description="They will lose access to this workspace. Their account and other workspaces are not affected." destructive confirmLabel="Remove member" busy={remove.isPending} onCancel={() => setRemoveMember(null)} onConfirm={() => removeMember && remove.mutate(removeMember)} />
      <ConfirmDialog open={deletingWorkspace} title={`Delete ${selectedWorkspace?.name ?? "workspace"}?`} description="This hides the workspace and its projects, tasks, notes, and documents from active views. Only the owner can confirm this action." destructive confirmLabel="Delete workspace" busy={deleteWorkspace.isPending} onCancel={() => setDeletingWorkspace(false)} onConfirm={() => deleteWorkspace.mutate()} />
    </div>
  );
}
