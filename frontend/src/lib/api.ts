export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function errorMessage(data: unknown, fallback: string): string {
  if (typeof data === "object" && data !== null && "detail" in data) {
    const detail = (data as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) return "Please check the submitted fields.";
  }
  return fallback;
}

export async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, options);
  if (response.status === 204) return undefined as T;
  let data: unknown = null;
  try {
    data = await response.json();
  } catch {
    // Convert non-JSON responses to safe messages below.
  }
  if (!response.ok) {
    throw new ApiError(errorMessage(data, `Request failed (${response.status})`), response.status);
  }
  return data as T;
}

export function authorizedRequest<T>(
  path: string,
  options: RequestInit,
  accessToken: string,
): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Authorization", `Bearer ${accessToken}`);
  if (options.body && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  return apiRequest<T>(path, { ...options, headers });
}

export function jsonRequest(method: string, body?: unknown): RequestInit {
  return {
    method,
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  };
}

export function toUserMessage(error: unknown, fallback = "Something went wrong. Please try again."): string {
  if (error instanceof ApiError) {
    if (error.status === 401) return "Your session has expired. Please sign in again.";
    if (error.status === 403) return "You do not have permission for this action.";
    if (error.status === 404) return "The requested item was not found or is unavailable.";
    if (error.status === 409) return error.message || "This action conflicts with the current state.";
    if (error.status === 413) return "The document is larger than the 5 MB limit.";
    if (error.status === 415) return "Only .txt and .md documents are supported.";
    if (error.status === 422) return error.message || "Please check the submitted fields.";
    if (error.status === 429) return "Too many requests. Please wait a moment and try again.";
    if (error.status >= 500) return "The service is temporarily unavailable. Please try again.";
  }
  return fallback;
}

export function formatBytes(value: number): string {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

export async function downloadDocument<T extends { content?: string; title: string; filename: string | null }>(
  request: <R>(path: string, options?: RequestInit) => Promise<R>,
  workspaceId: string,
  documentId: string,
  fallbackFilename: string,
): Promise<void> {
  const document = await request<T>(`/workspaces/${workspaceId}/documents/${documentId}`);
  const blob = new Blob([document.content ?? ""], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = window.document.createElement("a");
  anchor.href = url;
  anchor.download = document.filename ?? fallbackFilename ?? `${document.title}.txt`;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function formatDate(value: string | null, includeTime = false): string {
  if (!value) return "No date";
  const date = value.includes("T") ? new Date(value) : new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return "Invalid date";
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    year: "numeric",
    ...(includeTime ? { hour: "numeric", minute: "2-digit" } : {}),
  }).format(date);
}
