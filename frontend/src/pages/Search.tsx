import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { useAuth } from "../auth/AuthContext";
import { useWorkspace } from "../workspace/WorkspaceContext";
import type { SearchResponse } from "../types";
import { Icon } from "../components/Icon";
import { Badge, EmptyState, PageHeader, inputClass } from "../components/ui";
import { toUserMessage } from "../lib/api";

type SearchType = "all" | "document" | "meeting_note" | "task";
const tabs: Array<{ value: SearchType; label: string }> = [{ value: "all", label: "All" }, { value: "document", label: "Documents" }, { value: "meeting_note", label: "Meeting notes" }, { value: "task", label: "Tasks" }];

export function Search() {
  const { selectedWorkspace } = useWorkspace();
  const { fetchWithAuth } = useAuth();
  const [query, setQuery] = useState("");
  const [submitted, setSubmitted] = useState("");
  const [type, setType] = useState<SearchType>("all");
  const [response, setResponse] = useState<SearchResponse | null>(null);
  const search = useMutation({ mutationFn: ({ text, searchType }: { text: string; searchType: SearchType }) => fetchWithAuth<SearchResponse>(`/workspaces/${selectedWorkspace?.id}/search?q=${encodeURIComponent(text)}&limit=20${searchType === "all" ? "" : `&type=${searchType}`}`), onSuccess: (data) => setResponse(data) });
  function run(text: string, searchType: SearchType) { setSubmitted(text); search.mutate({ text, searchType }); }
  function submit(event: FormEvent) { event.preventDefault(); const text = query.trim(); if (text.length >= 2) run(text, type); }
  function selectType(next: SearchType) { setType(next); setResponse(null); if (submitted) run(submitted, next); }
  return (
    <div className="mx-auto max-w-5xl space-y-6"><PageHeader eyebrow={selectedWorkspace?.name} title="Search & Docs" description="Find project decisions, meeting notes, documents, and tasks across your workspace." actions={<Link to="/documents" className="btn-secondary"><Icon name="upload" />Add document</Link>} /><section className="card"><form onSubmit={submit} className="flex flex-col gap-3 sm:flex-row"><div className="relative flex-1"><Icon name="search" className="absolute left-4 top-3.5 h-5 w-5 text-slate-400" /><input aria-label="Semantic search query" required minLength={2} maxLength={300} className={`${inputClass} py-3 pl-11`} placeholder="Search your team’s collective memory…" value={query} onChange={(event) => setQuery(event.target.value)} /></div><button className="btn-primary px-6 py-3" disabled={search.isPending || query.trim().length < 2}>{search.isPending ? "Searching…" : "Search workspace"}</button></form><p className="mt-3 text-xs text-slate-500">Results are restricted to {selectedWorkspace?.name}. Choose a source below to narrow the same permission-aware search.</p></section>
      <div className="flex flex-wrap gap-2" role="tablist" aria-label="Search source filters">{tabs.map((tab) => <button key={tab.value} role="tab" aria-selected={type === tab.value} className={`rounded-xl px-4 py-2 text-sm font-medium transition ${type === tab.value ? "bg-indigo-600 text-white shadow-sm" : "border border-slate-200 bg-white text-slate-600 hover:border-indigo-200 hover:text-indigo-700"}`} onClick={() => selectType(tab.value)}>{tab.label}</button>)}</div>
      {search.isError && <div role="alert" className="rounded-xl bg-rose-50 p-4 text-sm text-rose-700">{toUserMessage(search.error)}</div>}{search.isPending ? <div className="space-y-3">{[1, 2, 3].map((item) => <div key={item} className="h-28 animate-pulse rounded-2xl bg-slate-200" />)}</div> : response ? response.items.length ? <div className="space-y-3"><p className="text-sm text-slate-500">{response.items.length} results for “{submitted}”{type !== "all" && ` in ${tabs.find((tab) => tab.value === type)?.label}`}</p>{response.items.map((result, index) => <article key={`${result.source_type}-${result.source_id}-${index}`} className="card p-5 transition hover:border-indigo-200"><div className="flex items-center gap-2"><Badge tone={result.source_type === "task" ? "indigo" : result.source_type === "document" ? "green" : "amber"}>{result.source_type.replaceAll("_", " ")}</Badge><span className="text-xs text-slate-400">{result.score === null ? "Ranked match" : `Score ${result.score.toFixed(3)}`}</span></div><h2 className="mt-3 font-semibold text-slate-900">{result.source_type === "task" ? <Link to={`/tasks/${result.source_id}`} className="hover:text-indigo-600">{result.title}</Link> : result.source_type === "document" ? <Link to="/documents" className="hover:text-indigo-600">{result.title}</Link> : result.source_type === "meeting_note" ? <Link to="/meeting-notes" className="hover:text-indigo-600">{result.title}</Link> : result.title}</h2><p className="mt-2 text-sm leading-6 text-slate-600">{result.snippet}</p></article>)}</div> : <EmptyState title="No relevant results" description="Try different wording, another source tab, or upload more team knowledge to the workspace." /> : <EmptyState title="Search your team’s collective memory" description="Try “payment launch blockers”, “authentication decision”, or “placement prep tasks”." />}</div>
  );
}
