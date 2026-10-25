import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "../auth/AuthContext";
import type { MemberList, Workspace, WorkspaceMember, WorkspaceRole } from "../types";

export type Permission = "view" | "edit" | "manage" | "owner" | "audit";

export function hasPermission(role: WorkspaceRole | null, permission: Permission): boolean {
  if (!role) return false;
  if (permission === "view") return true;
  if (permission === "edit") return ["OWNER", "ADMIN", "MEMBER"].includes(role);
  if (permission === "manage" || permission === "audit") return ["OWNER", "ADMIN"].includes(role);
  return role === "OWNER";
}

interface WorkspaceContextValue {
  workspaces: Workspace[];
  selectedWorkspace: Workspace | null;
  members: WorkspaceMember[];
  currentRole: WorkspaceRole | null;
  isLoading: boolean;
  selectWorkspace: (workspaceId: string) => void;
  refetchWorkspaces: () => Promise<unknown>;
  refetchMembers: () => Promise<unknown>;
}

const WorkspaceContext = createContext<WorkspaceContextValue | undefined>(undefined);
const STORAGE_KEY = "teampulse.selected_workspace";

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const { user, fetchWithAuth } = useAuth();
  const [selectedId, setSelectedId] = useState(() => localStorage.getItem(STORAGE_KEY));
  const workspacesQuery = useQuery({
    queryKey: ["workspaces"],
    queryFn: () => fetchWithAuth<Workspace[]>("/workspaces"),
    enabled: Boolean(user),
  });
  const workspaces = useMemo(() => workspacesQuery.data ?? [], [workspacesQuery.data]);

  useEffect(() => {
    if (!workspaces.length) {
      if (selectedId) setSelectedId(null);
      return;
    }
    if (!selectedId || !workspaces.some((workspace) => workspace.id === selectedId)) {
      setSelectedId(workspaces[0].id);
    }
  }, [selectedId, workspaces]);

  useEffect(() => {
    if (selectedId) localStorage.setItem(STORAGE_KEY, selectedId);
    else localStorage.removeItem(STORAGE_KEY);
  }, [selectedId]);

  const membersQuery = useQuery({
    queryKey: ["members", selectedId],
    queryFn: () => fetchWithAuth<MemberList>(`/workspaces/${selectedId}/members`),
    enabled: Boolean(user && selectedId),
  });
  const selectedWorkspace = workspaces.find((workspace) => workspace.id === selectedId) ?? null;
  const members = useMemo(() => membersQuery.data?.items ?? [], [membersQuery.data]);
  const currentRole = members.find((member) => member.user_id === user?.id)?.role ?? null;

  const value = useMemo<WorkspaceContextValue>(() => ({
    workspaces,
    selectedWorkspace,
    members,
    currentRole,
    isLoading: workspacesQuery.isLoading || (Boolean(selectedId) && membersQuery.isLoading),
    selectWorkspace: setSelectedId,
    refetchWorkspaces: workspacesQuery.refetch,
    refetchMembers: membersQuery.refetch,
  }), [workspaces, selectedWorkspace, members, currentRole, workspacesQuery.isLoading, membersQuery.isLoading, selectedId, workspacesQuery.refetch, membersQuery.refetch]);

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}

export function useWorkspace() {
  const context = useContext(WorkspaceContext);
  if (!context) throw new Error("useWorkspace must be used inside WorkspaceProvider");
  return context;
}

export function usePermissions() {
  const { currentRole } = useWorkspace();
  return {
    canView: hasPermission(currentRole, "view"),
    canEdit: hasPermission(currentRole, "edit"),
    canManage: hasPermission(currentRole, "manage"),
    canAudit: hasPermission(currentRole, "audit"),
    isOwner: hasPermission(currentRole, "owner"),
  };
}

export function RoleGate({ permission, children, fallback = null }: { permission: Permission; children: ReactNode; fallback?: ReactNode }) {
  const { currentRole } = useWorkspace();
  return hasPermission(currentRole, permission) ? children : fallback;
}
