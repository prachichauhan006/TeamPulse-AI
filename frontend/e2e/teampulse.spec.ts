import { randomBytes, randomUUID } from "node:crypto";
import { test, expect, request as playwrightRequest, type APIRequestContext, type Page } from "@playwright/test";

const API_BASE_URL = process.env.E2E_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";
type Tokens = { access_token: string; refresh_token: string };
type Identity = { email: string; password: string; tokens: Tokens };
type Workspace = { id: string; name: string };
type Project = { id: string; title: string };
type Task = { id: string; title: string };

let api: APIRequestContext;
let primary: Identity;
let outsider: Identity;

function unique(prefix: string) { return `${prefix}-${randomUUID().slice(0, 8)}`; }
function developmentPassword() { return `Aa1!${randomBytes(24).toString("base64url")}`; }
function headers(identity: Identity) { return { Authorization: `Bearer ${identity.tokens.access_token}` }; }

async function responseJSON<T>(response: Awaited<ReturnType<APIRequestContext["fetch"]>>, expected: number): Promise<T> {
  expect(response.status(), await response.text()).toBe(expected);
  return await response.json() as T;
}

async function createIdentity(label: string): Promise<Identity> {
  const email = `${unique(label)}@example.com`;
  const password = developmentPassword();
  await responseJSON(await api.post(`${API_BASE_URL}/auth/register`, { data: { full_name: `E2E ${label}`, email, password } }), 201);
  const tokens = await responseJSON<Tokens>(await api.post(`${API_BASE_URL}/auth/login`, { data: { email, password } }), 200);
  return { email, password, tokens };
}

async function createWorkspace(identity: Identity, label: string): Promise<Workspace> {
  return responseJSON<Workspace>(await api.post(`${API_BASE_URL}/workspaces`, { headers: headers(identity), data: { name: unique(label) } }), 201);
}

async function createProject(identity: Identity, workspace: Workspace, title: string): Promise<Project> {
  return responseJSON<Project>(await api.post(`${API_BASE_URL}/workspaces/${workspace.id}/projects`, { headers: headers(identity), data: { title, description: "Isolated Playwright project", status: "ACTIVE" } }), 201);
}

async function createTask(identity: Identity, workspace: Workspace, project: Project, title: string, status = "TODO"): Promise<Task> {
  return responseJSON<Task>(await api.post(`${API_BASE_URL}/workspaces/${workspace.id}/tasks`, { headers: headers(identity), data: { project_id: project.id, title, description: "Isolated Playwright task", status, priority: "HIGH" } }), 201);
}

async function authenticate(page: Page, identity: Identity, workspace?: Workspace) {
  await page.addInitScript(({ tokens, workspaceId }) => {
    localStorage.setItem("teampulse.access_token", tokens.access_token);
    localStorage.setItem("teampulse.refresh_token", tokens.refresh_token);
    if (workspaceId) localStorage.setItem("teampulse.selected_workspace", workspaceId);
  }, { tokens: identity.tokens, workspaceId: workspace?.id });
}

test.describe.configure({ mode: "serial" });

test.beforeAll(async () => {
  api = await playwrightRequest.newContext();
  primary = await createIdentity("primary");
  outsider = await createIdentity("outsider");
});

test.afterAll(async () => { await api.dispose(); });

test("registration, logout, and login use the real session flow", async ({ page }) => {
  const email = `${unique("ui-registration")}@example.com`;
  const password = developmentPassword();
  await page.goto("/register");
  await page.getByLabel("Full name").fill("Playwright Registration");
  await page.getByLabel("Email address").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByLabel("Confirm password").fill(password);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByRole("heading", { name: "Welcome to TeamPulse AI" })).toBeVisible();
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible();
  await page.getByLabel("Email address").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "Welcome to TeamPulse AI" })).toBeVisible();
});

test("workspace to project to task workflow", async ({ page }) => {
  await authenticate(page, primary);
  await page.goto("/");
  await page.getByRole("button", { name: "Create your first workspace" }).click();
  await page.getByLabel("Workspace name").fill(unique("UI Workspace"));
  await page.getByRole("button", { name: "Create workspace" }).click();
  const newProject = page.getByRole("button", { name: "New project" });
  await expect(newProject).toBeVisible();
  await newProject.click();
  await page.getByLabel("Project title").fill("UI Launch Project");
  await page.getByLabel("Description").fill("Created through the complete browser workflow.");
  await page.getByRole("button", { name: "Create project" }).click();
  await page.getByRole("link", { name: "Tasks", exact: true }).click();
  await page.getByRole("button", { name: "New task" }).click();
  await page.getByLabel("Project", { exact: true }).selectOption({ label: "UI Launch Project" });
  await page.getByLabel("Task title").fill("UI acceptance criteria");
  await page.getByLabel("Description").fill("Verify the end-to-end task flow.");
  await page.getByRole("button", { name: "Create task" }).click();
  await expect(page.getByRole("link", { name: "UI acceptance criteria" })).toBeVisible();
});

test("a blocked dependency explains downstream task risk", async ({ page }) => {
  const workspace = await createWorkspace(primary, "Dependency Risk");
  const project = await createProject(primary, workspace, "Payment Launch");
  const authentication = await createTask(primary, workspace, project, "Build authentication service", "BLOCKED");
  const payment = await createTask(primary, workspace, project, "Integrate payment API");
  await responseJSON(await api.post(`${API_BASE_URL}/workspaces/${workspace.id}/tasks/${payment.id}/dependencies`, { headers: headers(primary), data: { depends_on_task_id: authentication.id } }), 201);
  await authenticate(page, primary, workspace);
  await page.goto(`/tasks/${payment.id}`);
  await expect(page.getByText("AT RISK", { exact: true })).toBeVisible();
  await expect(page.getByTestId("risk-reasons")).toContainText("Dependency 'Build authentication service' is blocked.");
});

test("MockAIProvider plan stays a preview until explicit approval", async ({ page }) => {
  const workspace = await createWorkspace(primary, "AI Approval");
  await authenticate(page, primary, workspace);
  await page.goto("/ai-plan");
  await page.getByLabel("Paste your messy project brief").fill("Plan an isolated mobile launch with engineering and release readiness.");
  await page.getByRole("button", { name: "Generate plan preview" }).click();
  await expect(page.getByTestId("ai-plan-preview")).toContainText("AI suggestion — not saved yet");
  const before = await responseJSON<{ total: number }>(await api.get(`${API_BASE_URL}/workspaces/${workspace.id}/projects`, { headers: headers(primary) }), 200);
  expect(before.total).toBe(0);
  await page.getByRole("button", { name: "Approve and create" }).click();
  await expect(page.getByRole("heading", { name: "Plan approved" })).toBeVisible();
  const projects = await responseJSON<{ total: number }>(await api.get(`${API_BASE_URL}/workspaces/${workspace.id}/projects`, { headers: headers(primary) }), 200);
  const tasks = await responseJSON<{ total: number }>(await api.get(`${API_BASE_URL}/workspaces/${workspace.id}/tasks`, { headers: headers(primary) }), 200);
  expect(projects.total).toBe(1);
  expect(tasks.total).toBe(4);
});

test("tenant isolation hides another workspace and its tasks", async ({ page }) => {
  const ownWorkspace = await createWorkspace(primary, "Tenant A");
  const otherWorkspace = await createWorkspace(outsider, "Tenant B");
  const otherProject = await createProject(outsider, otherWorkspace, "Private project");
  const otherTask = await createTask(outsider, otherWorkspace, otherProject, "Private task");
  const foreignWorkspaceResponse = await api.get(`${API_BASE_URL}/workspaces/${otherWorkspace.id}/tasks`, { headers: headers(primary) });
  expect(foreignWorkspaceResponse.status()).toBe(403);
  const foreignTaskResponse = await api.get(`${API_BASE_URL}/workspaces/${ownWorkspace.id}/tasks/${otherTask.id}`, { headers: headers(primary) });
  expect(foreignTaskResponse.status()).toBe(404);
  await authenticate(page, primary, ownWorkspace);
  await page.goto("/");
  const switcher = page.getByLabel("Select workspace");
  await expect(switcher).toBeVisible();
  await expect(switcher.locator("option", { hasText: otherWorkspace.name })).toHaveCount(0);
  await expect(switcher.locator("option", { hasText: ownWorkspace.name })).toHaveCount(1);
});
