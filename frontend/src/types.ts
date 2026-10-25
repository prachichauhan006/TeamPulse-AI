export type WorkspaceRole = "OWNER" | "ADMIN" | "MEMBER" | "VIEWER";
export type ProjectStatus = "ACTIVE" | "ON_HOLD" | "COMPLETED" | "ARCHIVED";
export type TaskStatus = "TODO" | "IN_PROGRESS" | "BLOCKED" | "DONE";
export type TaskPriority = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type RiskStatus = "ON_TRACK" | "AT_RISK" | "OVERDUE" | "BLOCKED";
export type HealthStatus = "ON_TRACK" | "AT_RISK" | "CRITICAL";

export interface User { id: string; email: string; full_name: string; is_active: boolean; created_at: string; }
export interface TokenResponse { access_token: string; refresh_token: string; token_type: string; expires_in: number; }
export interface Workspace { id: string; name: string; created_at: string; updated_at: string; }
export interface WorkspaceMember { id: string; workspace_id: string; user_id: string; email: string; full_name: string; role: WorkspaceRole; created_at: string; updated_at: string; }
export interface MemberList { items: WorkspaceMember[]; total: number; }
export interface Project { id: string; workspace_id: string; title: string; description: string; status: ProjectStatus; created_by: string; created_at: string; updated_at: string; }
export interface ProjectHealth { project_id: string; health: HealthStatus; total_tasks: number; completed_tasks: number; blocked_tasks: number; overdue_tasks: number; at_risk_tasks: number; }
export interface Task { id: string; workspace_id: string; project_id: string; title: string; description: string; status: TaskStatus; priority: TaskPriority; assignee_id: string | null; due_date: string | null; created_by: string; version: number; created_at: string; updated_at: string; }
export interface TaskRisk { task_id: string; status: RiskStatus; reasons: string[]; }
export interface TaskDependency { id: string; task_id: string; depends_on_task_id: string; dependency_title: string; dependency_status: TaskStatus; dependency_due_date: string | null; created_at: string; }
export interface TaskView extends Task { project_title: string; assignee_name: string | null; dependency_ids: string[]; risk_status: RiskStatus; risk_reasons: string[]; }
export interface Paginated<T> { items: T[]; total: number; page: number; page_size: number; }

export interface AIPlanTask { key: string; title: string; description: string; priority: TaskPriority; suggested_assignee_id: string | null; suggested_assignee_name: string | null; due_date: string | null; depends_on: string[]; }
export interface AIPlan { project_title: string; summary: string; tasks: AIPlanTask[]; risks: string[]; assumptions: string[]; }
export interface MeetingAction { key: string; title: string; description: string; suggested_assignee_id: string | null; suggested_assignee_name: string | null; due_date: string | null; }
export interface MeetingExtraction { summary: string; decisions: string[]; action_items: MeetingAction[]; }
export interface AIProposalResult { project_id?: string; task_ids?: Record<string, string>; dependency_ids?: string[]; selected_action_item_keys?: string[]; }
export interface AIProposal<T = AIPlan | MeetingExtraction> { id: string; workspace_id: string; proposal_type: "PROJECT_PLAN" | "MEETING_ACTIONS"; status: "PENDING" | "APPROVED" | "REJECTED"; meeting_note_id: string | null; payload: T; result: AIProposalResult | null; created_by: string; reviewed_by: string | null; reviewed_at: string | null; created_at: string; updated_at: string; }
export interface MeetingNote { id: string; workspace_id: string; project_id: string | null; title: string; content?: string; embedding_status: string; embedding_error: string | null; created_by: string; created_at: string; updated_at: string; }
export interface TeamDocument { id: string; workspace_id: string; project_id: string | null; title: string; filename: string | null; mime_type: string; size_bytes: number; content?: string; embedding_status: string; embedding_error: string | null; created_by: string; created_at: string; updated_at: string; }
export interface DocumentList extends Paginated<TeamDocument> {}
export interface SearchResult { source_type: string; source_id: string; title: string; snippet: string; score: number | null; search_mode: string; }
export interface SearchResponse { query: string; mode: string; items: SearchResult[]; }
export interface DuplicateSuggestion { task_id: string; task_title: string; duplicate_task_id: string; duplicate_task_title: string; similarity: number; reason: string; }
export interface AuditLog { id: string; workspace_id: string | null; user_id: string | null; action: string; entity_type: string; entity_id: string | null; metadata: Record<string, unknown>; ip_address: string | null; created_at: string; }
export interface AuditListResponse extends Paginated<AuditLog> {}
export interface WeeklySummary { summary: string; highlights: string[]; recommended_actions: string[]; }
