import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "../auth/AuthContext";
import { useWorkspace } from "../workspace/WorkspaceContext";
import type { DuplicateSuggestion } from "../types";
import { Icon } from "./Icon";

export function DuplicateSuggestions() {
  const { selectedWorkspace } = useWorkspace();
  const { fetchWithAuth } = useAuth();
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());
  const query = useQuery({
    queryKey: ["duplicates", selectedWorkspace?.id],
    queryFn: () => fetchWithAuth<{ items: DuplicateSuggestion[] }>(`/workspaces/${selectedWorkspace?.id}/duplicate-task-suggestions`),
    enabled: Boolean(selectedWorkspace),
  });
  const items = (query.data?.items ?? []).filter((item) => !dismissed.has(`${item.task_id}:${item.duplicate_task_id}`));
  if (!items.length) return null;
  return (
    <section className="card border-amber-200 bg-amber-50/50">
      <div className="flex items-center gap-2"><Icon name="warning" className="h-5 w-5 text-amber-600" /><h2 className="font-semibold text-slate-900">Possible duplicate tasks</h2></div>
      <p className="mt-1 text-xs text-slate-500">Suggestions only — nothing is merged or deleted automatically.</p>
      <div className="mt-4 space-y-3">
        {items.map((item) => {
          const key = `${item.task_id}:${item.duplicate_task_id}`;
          return (
            <div key={key} className="flex items-start gap-3 rounded-xl bg-white p-3 text-sm ring-1 ring-amber-100">
              <div className="flex-1"><strong>{item.task_title}</strong><span className="mx-2 text-slate-400">↔</span><strong>{item.duplicate_task_title}</strong><p className="mt-1 text-xs text-slate-500">{item.reason}</p></div>
              <button type="button" className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100" onClick={() => setDismissed((current) => new Set(current).add(key))} aria-label={`Dismiss suggestion for ${item.task_title}`}><Icon name="close" className="h-4 w-4" /></button>
            </div>
          );
        })}
      </div>
    </section>
  );
}
