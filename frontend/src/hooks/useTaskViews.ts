import { useQueries } from "@tanstack/react-query";
import { useAuth } from "../auth/AuthContext";
import { useWorkspace } from "../workspace/WorkspaceContext";
import type { Project, Task, TaskDependency, TaskRisk, TaskView } from "../types";

/** The API intentionally exposes risk and dependencies as separate, scoped resources.
 * This hook composes them for board/list views without changing backend security rules.
 */
export function useTaskViews(tasks: Task[], projects: Project[] = []) {
  const { selectedWorkspace, members } = useWorkspace();
  const { fetchWithAuth } = useAuth();
  const workspaceId = selectedWorkspace?.id;
  const queries = useQueries({
    queries: tasks.map((task) => ({
      queryKey: ["task-enrichment", workspaceId, task.id, task.version],
      enabled: Boolean(workspaceId),
      queryFn: async () => {
        const [risk, dependencies] = await Promise.all([
          fetchWithAuth<TaskRisk>(`/workspaces/${workspaceId}/tasks/${task.id}/risk`),
          fetchWithAuth<TaskDependency[]>(`/workspaces/${workspaceId}/tasks/${task.id}/dependencies`),
        ]);
        return { risk, dependencies };
      },
    })),
  });
  const views: TaskView[] = tasks.map((task, index) => {
    const enrichment = queries[index]?.data;
    return {
      ...task,
      project_title: projects.find((project) => project.id === task.project_id)?.title ?? "Project",
      assignee_name: members.find((member) => member.user_id === task.assignee_id)?.full_name ?? null,
      dependency_ids: enrichment?.dependencies.map((dependency) => dependency.depends_on_task_id) ?? [],
      risk_status: enrichment?.risk.status ?? "ON_TRACK",
      risk_reasons: enrichment?.risk.reasons ?? [],
    };
  });
  return {
    views,
    isLoading: queries.some((query) => query.isLoading),
    isError: queries.some((query) => query.isError),
    refetch: () => Promise.all(queries.map((query) => query.refetch())),
  };
}
