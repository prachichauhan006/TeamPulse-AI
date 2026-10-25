import type { HealthStatus, ProjectStatus, RiskStatus, TaskPriority, TaskStatus } from "../types";

const statusStyles: Record<TaskStatus, string> = {
  TODO: "bg-slate-100 text-slate-700 ring-slate-200",
  IN_PROGRESS: "bg-indigo-50 text-indigo-700 ring-indigo-200",
  BLOCKED: "bg-rose-50 text-rose-700 ring-rose-200",
  DONE: "bg-emerald-50 text-emerald-700 ring-emerald-200",
};

const statusLabels: Record<TaskStatus, string> = {
  TODO: "To Do",
  IN_PROGRESS: "In Progress",
  BLOCKED: "Blocked",
  DONE: "Done",
};

export function TaskStatusBadge({ status }: { status: TaskStatus }) {
  return <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold ring-1 ring-inset ${statusStyles[status]}`}><span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden="true" />{statusLabels[status]}</span>;
}

export function PriorityBadge({ priority }: { priority: TaskPriority }) {
  const styles: Record<TaskPriority, string> = {
    LOW: "bg-slate-50 text-slate-600 ring-slate-200",
    MEDIUM: "bg-sky-50 text-sky-700 ring-sky-200",
    HIGH: "bg-amber-50 text-amber-800 ring-amber-200",
    CRITICAL: "bg-rose-50 text-rose-700 ring-rose-200",
  };
  return <span className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide ring-1 ring-inset ${styles[priority]}`}>{priority}</span>;
}

export function RiskPill({ status }: { status: RiskStatus }) {
  if (status === "ON_TRACK") return null;
  const styles: Record<Exclude<RiskStatus, "ON_TRACK">, string> = {
    AT_RISK: "bg-amber-50 text-amber-800 ring-amber-200",
    OVERDUE: "bg-orange-50 text-orange-700 ring-orange-200",
    BLOCKED: "bg-rose-50 text-rose-700 ring-rose-200",
  };
  return <span className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide ring-1 ring-inset ${styles[status]}`}>{status.replaceAll("_", " ")}</span>;
}

export function HealthBadge({ health }: { health: HealthStatus }) {
  const styles: Record<HealthStatus, string> = {
    ON_TRACK: "bg-emerald-50 text-emerald-700 ring-emerald-200",
    AT_RISK: "bg-amber-50 text-amber-800 ring-amber-200",
    CRITICAL: "bg-rose-50 text-rose-700 ring-rose-200",
  };
  return <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${styles[health]}`}><span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden="true" />{health.replaceAll("_", " ")}</span>;
}

export function ProjectStatusBadge({ status }: { status: ProjectStatus }) {
  const styles: Record<ProjectStatus, string> = {
    ACTIVE: "bg-indigo-50 text-indigo-700 ring-indigo-200",
    ON_HOLD: "bg-amber-50 text-amber-800 ring-amber-200",
    COMPLETED: "bg-emerald-50 text-emerald-700 ring-emerald-200",
    ARCHIVED: "bg-slate-100 text-slate-600 ring-slate-200",
  };
  return <span className={`inline-flex rounded-full px-2.5 py-1 text-[11px] font-semibold ring-1 ring-inset ${styles[status]}`}>{status.replaceAll("_", " ")}</span>;
}
