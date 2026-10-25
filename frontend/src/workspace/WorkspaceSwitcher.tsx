import { useWorkspace } from "./WorkspaceContext";

export function WorkspaceSwitcher() {
  const { workspaces, selectedWorkspace, selectWorkspace } = useWorkspace();
  if (!workspaces.length) return <span className="text-sm text-slate-500">No workspaces</span>;
  return (
    <label className="block">
      <span className="sr-only">Select workspace</span>
      <select
        aria-label="Select workspace"
        className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm"
        value={selectedWorkspace?.id ?? ""}
        onChange={(event) => selectWorkspace(event.target.value)}
      >
        {workspaces.map((workspace) => (
          <option key={workspace.id} value={workspace.id}>{workspace.name}</option>
        ))}
      </select>
    </label>
  );
}
