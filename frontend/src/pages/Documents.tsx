import { useRef, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "../auth/AuthContext";
import { usePermissions, useWorkspace } from "../workspace/WorkspaceContext";
import type { DocumentList, TeamDocument } from "../types";
import { Icon } from "../components/Icon";
import { Badge, ConfirmDialog, EmptyState, ErrorState, LoadingState, PageHeader } from "../components/ui";
import { downloadDocument, formatBytes, formatDate, toUserMessage } from "../lib/api";
import { useToast } from "../components/Toast";

export function Documents() {
  const { selectedWorkspace } = useWorkspace();
  const { canEdit } = usePermissions();
  const { fetchWithAuth } = useAuth();
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const fileInput = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const workspaceId = selectedWorkspace?.id;
  const documents = useQuery({ queryKey: ["documents", workspaceId], queryFn: () => fetchWithAuth<DocumentList>(`/workspaces/${workspaceId}/documents?page_size=100`), enabled: Boolean(workspaceId) });
  const upload = useMutation({ mutationFn: () => { const body = new FormData(); if (file) body.append("file", file); return fetchWithAuth<TeamDocument>(`/workspaces/${workspaceId}/documents`, { method: "POST", body }); }, onSuccess: () => { showToast("Document uploaded and queued for indexing."); setFile(null); if (fileInput.current) fileInput.current.value = ""; void queryClient.invalidateQueries({ queryKey: ["documents", workspaceId] }); }, onError: (error) => showToast(toUserMessage(error), "error") });
  const remove = useMutation({ mutationFn: (id: string) => fetchWithAuth<void>(`/workspaces/${workspaceId}/documents/${id}`, { method: "DELETE" }), onSuccess: () => { showToast("Document deleted."); setDeleteId(null); void queryClient.invalidateQueries({ queryKey: ["documents", workspaceId] }); }, onError: (error) => showToast(toUserMessage(error), "error") });
  function submit(event: FormEvent) { event.preventDefault(); if (file) upload.mutate(); }
  return (
    <div className="space-y-6"><PageHeader eyebrow={selectedWorkspace?.name} title="Documents" description="Add source material for Search & Docs. Files remain isolated to this workspace." actions={<Link to="/search" className="btn-secondary"><Icon name="search" />Search & Docs</Link>} />
      {canEdit && <section className="card"><form onSubmit={submit} className="flex flex-col gap-4 sm:flex-row sm:items-end"><label className="flex-1 text-sm font-medium text-slate-700">Choose a document<input ref={fileInput} type="file" accept=".txt,.md,text/plain,text/markdown" required className="mt-2 block w-full rounded-xl border border-dashed border-slate-300 bg-slate-50 p-4 text-sm file:mr-4 file:rounded-lg file:border-0 file:bg-indigo-50 file:px-3 file:py-2 file:font-medium file:text-indigo-700" onChange={(event) => setFile(event.target.files?.[0] ?? null)} /><span className="mt-2 block text-xs font-normal text-slate-500">UTF-8 .txt and .md files only. Size limits are enforced by the server.</span></label><button className="btn-primary shrink-0" disabled={!file || upload.isPending}>{upload.isPending ? "Uploading…" : <><Icon name="upload" />Upload document</>}</button></form></section>}
      <section className="card"><div className="flex items-center justify-between"><h2 className="font-semibold">Workspace files</h2><span className="text-sm text-slate-500">{documents.data?.total ?? 0} total</span></div>{documents.isLoading ? <LoadingState /> : documents.isError ? <ErrorState onRetry={() => void documents.refetch()} /> : documents.data?.items.length ? <div className="mt-4 divide-y divide-slate-100">{documents.data.items.map((document) => <div key={document.id} className="flex flex-col gap-3 py-4 first:pt-0 last:pb-0 sm:flex-row sm:items-center"><div className="rounded-xl bg-indigo-50 p-3 text-indigo-600"><Icon name="documents" className="h-5 w-5" /></div><div className="min-w-0 flex-1"><p className="truncate font-medium text-slate-900">{document.title}</p><p className="mt-1 text-xs text-slate-500">{document.filename ?? "Pasted text"} · {formatBytes(document.size_bytes)} · {formatDate(document.created_at)}</p><Badge tone={document.embedding_status === "COMPLETE" ? "green" : document.embedding_status === "FAILED" ? "red" : "slate"}>{document.embedding_status.toLowerCase()} indexing</Badge></div><div className="flex gap-2"><button className="btn-secondary" onClick={async () => { try { await downloadDocument<TeamDocument>(fetchWithAuth, workspaceId ?? "", document.id, document.filename ?? `${document.title}.txt`); } catch (error) { showToast(toUserMessage(error), "error"); } }}>Download</button>{canEdit && <button className="rounded-xl p-2 text-slate-400 hover:bg-rose-50 hover:text-rose-600" aria-label={`Delete ${document.title}`} onClick={() => setDeleteId(document.id)}><Icon name="trash" className="h-5 w-5" /></button>}</div></div>)}</div> : <EmptyState title="No documents yet" description="Upload product specs, meeting records, or team knowledge to make them searchable." />}</section>
      <ConfirmDialog open={Boolean(deleteId)} title="Delete this document?" description="The uploaded file and its search index data will be removed from active views. This cannot be undone." destructive confirmLabel="Delete document" busy={remove.isPending} onCancel={() => setDeleteId(null)} onConfirm={() => deleteId && remove.mutate(deleteId)} />
    </div>
  );
}
