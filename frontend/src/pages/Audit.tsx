import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "../auth/AuthContext";
import { usePermissions, useWorkspace } from "../workspace/WorkspaceContext";
import type { AuditListResponse } from "../types";
import { EmptyState, ErrorState, LoadingState, PageHeader, Badge } from "../components/ui";
import { formatDate } from "../lib/api";

function actionTone(action: string): "slate" | "green" | "amber" | "red" | "indigo" {
  if (action.includes("APPROVED")) return "green";
  if (action.includes("DELETED") || action.includes("REJECTED")) return "red";
  if (action.includes("UPDATED") || action.includes("STATUS")) return "amber";
  return "indigo";
}

export function Audit() {
  const { selectedWorkspace, members } = useWorkspace();
  const { canAudit } = usePermissions();
  const { fetchWithAuth } = useAuth();
  const [page, setPage] = useState(1);
  const workspaceId = selectedWorkspace?.id;
  const query = useQuery({ queryKey: ["audit", workspaceId, page], queryFn: () => fetchWithAuth<AuditListResponse>(`/workspaces/${workspaceId}/audit-logs?page=${page}&page_size=25`), enabled: Boolean(workspaceId && canAudit) });
  if (!canAudit) return <EmptyState title="Admin access required" description="Audit activity is available to workspace owners and admins. Your role does not permit access." />;
  const totalPages = Math.max(1, Math.ceil((query.data?.total ?? 0) / 25));
  return <div className="space-y-6"><PageHeader eyebrow={selectedWorkspace?.name} title="Audit Activity" description="A compact, paginated record of workspace changes and AI approval decisions." /><section className="card overflow-hidden p-0">{query.isLoading ? <LoadingState /> : query.isError ? <ErrorState onRetry={() => void query.refetch()} /> : query.data?.items.length ? <><div className="overflow-x-auto"><table className="w-full min-w-[680px] text-left text-sm"><thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-400"><tr><th className="px-5 py-3 font-semibold">Time</th><th className="px-5 py-3 font-semibold">Actor</th><th className="px-5 py-3 font-semibold">Action</th><th className="px-5 py-3 font-semibold">Entity</th></tr></thead><tbody className="divide-y divide-slate-100">{query.data.items.map((item) => <tr key={item.id} className="hover:bg-slate-50/70"><td className="whitespace-nowrap px-5 py-3.5 text-xs text-slate-500">{formatDate(item.created_at, true)}</td><td className="px-5 py-3.5 text-sm font-medium text-slate-700">{item.user_id ? members.find((member) => member.user_id === item.user_id)?.full_name ?? `User ${item.user_id.slice(0, 8)}` : "System"}</td><td className="px-5 py-3.5"><Badge tone={actionTone(item.action)}>{item.action.replaceAll("_", " ")}</Badge></td><td className="px-5 py-3.5"><span className="inline-flex rounded-lg bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600">{item.entity_type}</span><span className="ml-2 font-mono text-xs text-slate-400">{item.entity_id?.slice(0, 8) ?? "—"}</span></td></tr>)}</tbody></table></div><div className="flex items-center justify-between border-t border-slate-100 p-4"><p className="text-sm text-slate-500">Page {page} of {totalPages} · {query.data.total} events</p><div className="flex gap-2"><button className="btn-secondary" disabled={page <= 1} onClick={() => setPage((value) => value - 1)}>Previous</button><button className="btn-secondary" disabled={page >= totalPages} onClick={() => setPage((value) => value + 1)}>Next</button></div></div></> : <EmptyState title="No audit events yet" description="Important workspace changes will appear here." />}</section></div>;
}
