import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  DndContext,
  DragOverlay,
  KeyboardSensor,
  PointerSensor,
  closestCorners,
  useDroppable,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragOverEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { SortableContext, sortableKeyboardCoordinates, useSortable, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import type { TaskStatus, TaskView } from "../types";
import { formatDate } from "../lib/api";
import { Icon } from "./Icon";
import { PriorityBadge, RiskPill } from "./StatusBadge";

export const KANBAN_COLUMNS: Array<{ status: TaskStatus; label: string; tint: string }> = [
  { status: "TODO", label: "To Do", tint: "bg-slate-400" },
  { status: "IN_PROGRESS", label: "In Progress", tint: "bg-indigo-500" },
  { status: "BLOCKED", label: "Blocked", tint: "bg-rose-500" },
  { status: "DONE", label: "Done", tint: "bg-emerald-500" },
];

const statusOptions = KANBAN_COLUMNS.map(({ status, label }) => ({ status, label }));

export function resolveKanbanDrop(activeId: string, overId: string | null, tasks: TaskView[]): TaskStatus | null {
  const activeTask = tasks.find((task) => task.id === activeId);
  if (!activeTask || !overId) return null;
  const overTask = tasks.find((task) => task.id === overId);
  if (overTask) return overTask.status;
  return KANBAN_COLUMNS.some((column) => column.status === overId) ? overId as TaskStatus : null;
}

/** Kept separate from the sensor wiring so permission and status-update behavior are unit-testable. */
export function handleKanbanDragEnd(event: Pick<DragEndEvent, "active" | "over">, tasks: TaskView[], canEdit: boolean, onStatusChange: (task: TaskView, status: TaskStatus) => void) {
  if (!canEdit || !event.over) return;
  const task = tasks.find((item) => item.id === String(event.active.id));
  const nextStatus = resolveKanbanDrop(String(event.active.id), String(event.over.id), tasks);
  if (task && nextStatus && nextStatus !== task.status) onStatusChange(task, nextStatus);
}

function initials(name: string | null) {
  return name ? name.split(/\s+/).map((part) => part[0]).join("").slice(0, 2).toUpperCase() : "?";
}

export function TaskCardContent({ task, overlay = false }: { task: TaskView; overlay?: boolean }) {
  return (
    <div className={overlay ? "pointer-events-none" : ""}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex flex-wrap items-center gap-1.5"><PriorityBadge priority={task.priority} /><RiskPill status={task.risk_status} /></div>
        <span className="max-w-[7rem] truncate text-[10px] font-medium text-slate-400" title={task.project_title}>{task.project_title}</span>
      </div>
      <Link to={`/tasks/${task.id}`} className="mt-3 block text-sm font-semibold leading-5 text-slate-900 transition hover:text-indigo-700">{task.title}</Link>
      <div className="mt-4 flex items-center justify-between gap-2 border-t border-slate-100 pt-3">
        <div className="flex min-w-0 items-center gap-2">
          <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-[10px] font-bold text-indigo-700" title={task.assignee_name ?? "Unassigned"}>{initials(task.assignee_name)}</span>
          <span className="truncate text-xs text-slate-500">{task.assignee_name ?? "Unassigned"}</span>
        </div>
        <span className={`shrink-0 text-[11px] font-medium ${task.risk_status === "OVERDUE" ? "text-rose-600" : "text-slate-500"}`}>{task.due_date ? formatDate(task.due_date) : "No due date"}</span>
      </div>
      {task.dependency_ids.length > 0 && <div className="mt-3 flex items-center gap-1.5 text-[11px] text-slate-500" title={`${task.dependency_ids.length} blocking or prerequisite ${task.dependency_ids.length === 1 ? "dependency" : "dependencies"}`}><Icon name="link" className="h-3.5 w-3.5" />{task.dependency_ids.length} {task.dependency_ids.length === 1 ? "dependency" : "dependencies"}</div>}
    </div>
  );
}

function SortableTaskCard({ task, canEdit, onStatusChange }: { task: TaskView; canEdit: boolean; onStatusChange: (task: TaskView, status: TaskStatus) => void }) {
  const { attributes, listeners, setNodeRef, setActivatorNodeRef, transform, transition, isDragging } = useSortable({ id: task.id, disabled: !canEdit, data: { type: "task", status: task.status } });
  return (
    <article ref={setNodeRef} style={{ transform: CSS.Transform.toString(transform), transition }} className={`rounded-2xl border border-slate-200 bg-white p-4 shadow-sm transition ${isDragging ? "z-10 opacity-30" : "hover:-translate-y-0.5 hover:border-indigo-200 hover:shadow-md"}`} data-task-id={task.id} data-draggable={canEdit ? "true" : "false"}>
      <div className="flex items-start gap-1">
        <div className="min-w-0 flex-1"><TaskCardContent task={task} /></div>
        <button
          ref={setActivatorNodeRef}
          type="button"
          {...attributes}
          {...(canEdit ? listeners : {})}
          disabled={!canEdit}
          aria-label={canEdit ? `Drag ${task.title}` : `Drag disabled for ${task.title}`}
          title={canEdit ? "Drag to change status" : "Your role cannot change task status"}
          className="-mr-2 -mt-1 shrink-0 rounded-lg p-1.5 text-slate-300 transition hover:bg-indigo-50 hover:text-indigo-600 disabled:cursor-not-allowed disabled:opacity-40"
        ><Icon name="grip" className="h-4 w-4" /></button>
      </div>
      {canEdit && <label className="mt-3 flex items-center gap-2 border-t border-slate-100 pt-3 text-[11px] font-medium text-slate-500">
        <span>Status</span>
        <select
          aria-label={`Status for ${task.title}`}
          className="min-w-0 flex-1 rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-xs text-slate-700 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
          value={task.status}
          onChange={(event) => onStatusChange(task, event.target.value as TaskStatus)}
        >
          {statusOptions.map((option) => <option key={option.status} value={option.status}>{option.label}</option>)}
        </select>
      </label>}
    </article>
  );
}

function KanbanColumn({ status, label, tint, tasks, canEdit, highlighted, onStatusChange }: { status: TaskStatus; label: string; tint: string; tasks: TaskView[]; canEdit: boolean; highlighted: boolean; onStatusChange: (task: TaskView, status: TaskStatus) => void }) {
  const { setNodeRef, isOver } = useDroppable({ id: status, data: { type: "column", status } });
  return (
    <section ref={setNodeRef} data-testid={`kanban-column-${status}`} data-drop-column={status} aria-label={`${label} drop column`} className={`flex min-h-[26rem] flex-col rounded-2xl border p-3 transition ${isOver || highlighted ? "border-indigo-400 bg-indigo-50/80 ring-2 ring-indigo-200" : "border-slate-200/80 bg-slate-100/60"}`}>
      <header className="mb-3 flex items-center justify-between px-1"><h2 className="flex items-center gap-2 text-sm font-semibold text-slate-800"><span className={`h-2 w-2 rounded-full ${tint}`} aria-hidden="true" />{label}</h2><span className="rounded-full bg-white px-2 py-0.5 text-xs font-semibold text-slate-500 ring-1 ring-slate-200">{tasks.length}</span></header>
      <SortableContext items={tasks.map((task) => task.id)} strategy={verticalListSortingStrategy}>
        <div className="flex flex-1 flex-col gap-3">
          {tasks.map((task) => <SortableTaskCard key={task.id} task={task} canEdit={canEdit} onStatusChange={onStatusChange} />)}
          {!tasks.length && <div className="flex min-h-32 flex-1 items-center justify-center rounded-xl border border-dashed border-slate-300 px-4 text-center text-xs leading-5 text-slate-400">Drop a task here</div>}
        </div>
      </SortableContext>
    </section>
  );
}

export function KanbanBoard({ tasks, canEdit, onStatusChange }: { tasks: TaskView[]; canEdit: boolean; onStatusChange: (task: TaskView, status: TaskStatus) => void }) {
  const [activeId, setActiveId] = useState<string | null>(null);
  const [overId, setOverId] = useState<string | null>(null);
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );
  const activeTask = tasks.find((task) => task.id === activeId);
  const overTask = tasks.find((task) => task.id === overId);
  const highlightedStatus = overTask?.status ?? (KANBAN_COLUMNS.some((column) => column.status === overId) ? overId as TaskStatus : null);
  const grouped = useMemo(() => Object.fromEntries(KANBAN_COLUMNS.map((column) => [column.status, tasks.filter((task) => task.status === column.status)])) as Record<TaskStatus, TaskView[]>, [tasks]);

  function onDragStart(event: DragStartEvent) { setActiveId(String(event.active.id)); setOverId(null); }
  function onDragOver(event: DragOverEvent) { setOverId(event.over ? String(event.over.id) : null); }
  function reset() { setActiveId(null); setOverId(null); }

  return (
    <div>
      <div className="mb-3 flex items-center justify-between gap-3 text-xs text-slate-500"><p>{canEdit ? "Drag cards between columns or use the keyboard drag handle." : "Your role has read-only access. Dragging is disabled."}</p><span className="hidden sm:inline">Same-column order is visual only.</span></div>
      <DndContext sensors={sensors} collisionDetection={closestCorners} onDragStart={onDragStart} onDragOver={onDragOver} onDragEnd={(event) => { handleKanbanDragEnd(event, tasks, canEdit, onStatusChange); reset(); }} onDragCancel={reset}>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {KANBAN_COLUMNS.map((column) => <KanbanColumn key={column.status} {...column} tasks={grouped[column.status]} canEdit={canEdit} highlighted={highlightedStatus === column.status && Boolean(activeId)} onStatusChange={onStatusChange} />)}
        </div>
        <DragOverlay>{activeTask ? <div className="w-72 rotate-2 rounded-2xl border border-indigo-300 bg-white p-4 shadow-2xl"><TaskCardContent task={activeTask} overlay /></div> : null}</DragOverlay>
      </DndContext>
    </div>
  );
}
