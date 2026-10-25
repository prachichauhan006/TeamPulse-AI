import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { useAuth } from "../auth/AuthContext";
import { usePermissions, useWorkspace } from "../workspace/WorkspaceContext";
import type { AIPlan, AIProposal } from "../types";
import { PlanPreview } from "../components/PlanPreview";
import { Icon } from "../components/Icon";
import { EmptyState, PageHeader, inputClass, labelClass } from "../components/ui";
import { jsonRequest, toUserMessage } from "../lib/api";
import { useToast } from "../components/Toast";

export function AIGenerator() {
  const { selectedWorkspace } = useWorkspace();
  const { canManage } = usePermissions();
  const { fetchWithAuth } = useAuth();
  const { showToast } = useToast();
  const [prompt, setPrompt] = useState("");
  const [proposal, setProposal] = useState<AIProposal<AIPlan> | null>(null);
  const [createdProject, setCreatedProject] = useState<{ project_id: string; task_ids: string[] } | null>(null);
  const generate = useMutation({ mutationFn: () => fetchWithAuth<AIProposal<AIPlan>>(`/workspaces/${selectedWorkspace?.id}/ai/plans/preview`, jsonRequest("POST", { brief: prompt })), onSuccess: (data) => { setProposal(data); setCreatedProject(null); } });
  const approve = useMutation({
    mutationFn: () => fetchWithAuth<AIProposal<AIPlan>>(`/workspaces/${selectedWorkspace?.id}/ai/proposals/${proposal?.id}/approve`, jsonRequest("POST", {})),
    onSuccess: (data) => { const projectId = data.result?.project_id; if (projectId) setCreatedProject({ project_id: projectId, task_ids: Object.values(data.result?.task_ids ?? {}) }); showToast("Plan approved. Project and tasks created."); },
    onError: (error) => showToast(toUserMessage(error), "error"),
  });
  const reject = useMutation({ mutationFn: () => fetchWithAuth<AIProposal<AIPlan>>(`/workspaces/${selectedWorkspace?.id}/ai/proposals/${proposal?.id}/reject`, jsonRequest("POST", {})), onSuccess: (data) => { setProposal(data); showToast("Suggestion rejected. Nothing was created."); }, onError: (error) => showToast(toUserMessage(error), "error") });
  if (!canManage) return <EmptyState title="AI planning requires admin access" description="Workspace owners and admins can generate and approve AI plans. Your existing work remains available in the other sections." />;
  return (
    <div className="space-y-6"><PageHeader eyebrow="Human in the loop" title="AI Project Plan Generator" description="Turn a goal into a reviewable project plan. The AI can suggest, but only you can approve changes." />
      <div className="grid gap-6 xl:grid-cols-[0.8fr_1.5fr]"><section className="card h-fit xl:sticky xl:top-28"><div className="flex items-center gap-3"><div className="rounded-xl bg-indigo-50 p-2 text-indigo-600"><Icon name="sparkles" className="h-5 w-5" /></div><div><h2 className="font-semibold">Paste your messy project brief</h2><p className="text-xs text-slate-500">Workspace context is added securely.</p></div></div><form className="mt-5 space-y-4" onSubmit={(event) => { event.preventDefault(); generate.mutate(); }}><label className={labelClass}>Paste your messy project brief<textarea required minLength={20} maxLength={100000} rows={9} className={inputClass} value={prompt} onChange={(event) => setPrompt(event.target.value)} placeholder="Plan a mobile app launch for our existing customers, including design, engineering, QA, and release coordination…" /></label><div className="flex items-center justify-between text-xs text-slate-400"><span>Minimum 20 characters</span><span>{prompt.length.toLocaleString()} / 100,000</span></div>{generate.isError && <p role="alert" className="rounded-xl bg-rose-50 p-3 text-sm text-rose-700">{toUserMessage(generate.error)}</p>}<button className="btn-primary w-full" disabled={generate.isPending || prompt.trim().length < 20}>{generate.isPending ? <><span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />Generating preview…</> : <><Icon name="sparkles" />Generate plan preview</>}</button><p className="text-center text-xs font-medium text-slate-500">Nothing is saved until you approve.</p></form><div className="mt-5 rounded-xl bg-slate-50 p-3 text-xs leading-5 text-slate-500"><strong className="text-slate-700">Safety by design:</strong> untrusted output is validated, assignee references are checked, and dependencies are checked for cycles before approval.</div></section>
        <div>{createdProject ? <div className="card text-center"><div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-emerald-100 text-emerald-600"><Icon name="check" className="h-7 w-7" /></div><h2 className="mt-4 text-2xl font-bold">Plan approved</h2><p className="mt-2 text-slate-600">Created one project and {createdProject.task_ids.length} tasks with validated dependencies.</p><Link to={`/tasks?project=${createdProject.project_id}`} className="btn-primary mt-6">Open project tasks</Link><button className="btn-secondary ml-2 mt-6" onClick={() => { setProposal(null); setCreatedProject(null); setPrompt(""); }}>Start another</button></div> : proposal ? <PlanPreview proposal={proposal} busy={approve.isPending || reject.isPending} onApprove={() => approve.mutate()} onReject={() => reject.mutate()} /> : <EmptyState title="Your plan preview will appear here" description="Include your desired outcome, timeline, team constraints, and major deliverables for a more useful suggestion." />}</div>
      </div>
    </div>
  );
}
