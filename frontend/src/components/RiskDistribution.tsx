import type { RiskStatus, TaskView } from "../types";

const items: Array<{ status: RiskStatus; label: string; color: string }> = [
  { status: "ON_TRACK", label: "On track", color: "bg-emerald-500" },
  { status: "AT_RISK", label: "At risk", color: "bg-amber-400" },
  { status: "OVERDUE", label: "Overdue", color: "bg-orange-500" },
  { status: "BLOCKED", label: "Blocked", color: "bg-rose-500" },
];

export function RiskDistribution({ tasks }: { tasks: TaskView[] }) {
  const counts = items.map((item) => ({ ...item, count: tasks.filter((task) => task.risk_status === item.status).length }));
  const total = tasks.length;
  const summary = counts.map((item) => `${item.label}: ${item.count}`).join(", ");
  return (
    <section className="card" aria-labelledby="risk-distribution-title">
      <div className="flex items-start justify-between gap-3"><div><h2 id="risk-distribution-title" className="font-semibold text-slate-900">Risk distribution</h2><p className="mt-1 text-xs text-slate-500">Deterministic risk across all workspace tasks.</p></div><span className="rounded-lg bg-slate-100 px-2 py-1 text-xs font-semibold text-slate-600">{total} tasks</span></div>
      {total ? <>
        <div className="mt-6 flex h-3 overflow-hidden rounded-full bg-slate-100" role="img" aria-label={`Task risk distribution. ${summary}`}>
          {counts.map((item) => item.count > 0 && <span key={item.status} className={`${item.color} h-full`} style={{ width: `${(item.count / total) * 100}%` }} aria-hidden="true" />)}
        </div>
        <ul className="mt-5 grid grid-cols-2 gap-3" aria-label="Risk distribution details">
          {counts.map((item) => <li key={item.status} className="flex items-center justify-between gap-2 text-sm"><span className="flex items-center gap-2 text-slate-600"><span className={`h-2.5 w-2.5 rounded-full ${item.color}`} aria-hidden="true" />{item.label}</span><strong className="text-slate-900">{item.count}</strong></li>)}
        </ul>
      </> : <p className="mt-6 rounded-xl bg-slate-50 p-4 text-sm text-slate-500">No tasks yet. Risk will appear after work is created.</p>}
    </section>
  );
}
