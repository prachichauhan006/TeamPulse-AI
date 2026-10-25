# TeamPulse AI — Interview Demo Guide

## Demo goals

Show four things clearly:

1. A real multi-tenant team workflow, not a static dashboard.
2. Explainable dependency risk and workspace RBAC.
3. AI assistance with a visible human approval boundary.
4. Engineering evidence: tests, audit records, provider abstraction, and honest limitations.

Allow 12–15 minutes for the main path and another 5 minutes for architecture/questions.

## Before the interview

### Runtime checklist

- Docker Engine and Compose v2 are running.
- `.env` exists only locally with independent random `JWT_SECRET_KEY` and local `POSTGRES_PASSWORD`.
- `AI_PROVIDER=mock`; no real AI key is needed or shown.
- All migrations have been applied.
- Backend, frontend, Redis, PostgreSQL, and Celery worker are healthy.
- The rich seed has been run with a development-only password entered through a hidden prompt.
- Browser zoom is comfortable and unrelated tabs/notifications are closed.

### Setup commands

```bash
cp .env.example .env
# Edit .env locally; do not display secret values.
docker compose build
docker compose up -d db redis
docker compose run --rm backend alembic upgrade head
docker compose up -d
read -rsp "Development seed password: " SEED_USER_PASSWORD; echo
docker compose exec -e SEED_USER_PASSWORD="$SEED_USER_PASSWORD" backend python -m app.db.seed
unset SEED_USER_PASSWORD
docker compose ps
```

Open <http://localhost:5173> and <http://localhost:8000/docs> in separate tabs. Do not open `.env`, shell history, token storage, or password values on screen.

### Demo identities

All four use the runtime-only seed password:

| Email | Role | Purpose |
|---|---|---|
| `owner.demo@teampulse.app` | OWNER | Main demo, full administration |
| `admin.demo@teampulse.app` | ADMIN | Project/plan/member administration |
| `member.demo@teampulse.app` | MEMBER | Task/note/document workflows |
| `viewer.demo@teampulse.app` | VIEWER | Read-only dashboard, board, and search |

Do not read the password aloud or include it in notes, screenshots, or a resume.

## Main demo script

### 1. Product framing — 45 seconds

Say:

> “TeamPulse AI brings projects, dependencies, meeting actions, and team knowledge into one workspace. The important constraint is that AI can suggest work, but it cannot write projects or tasks without explicit approval.”

Show the sign-in screen and sign in as the demo owner.

### 2. Dashboard and workspace isolation — 60 seconds

- Confirm **Placement Prep Team** in the workspace switcher.
- Explain that the selected workspace drives every subsequent API query.
- Point out active project/open-task/risk metrics and the weekly briefing.
- Mention that the briefing uses the same provider abstraction and is read-only.

Talking point:

> “The UI mirrors permissions for usability, but FastAPI enforces membership and RBAC independently on every request.”

### 3. Team and RBAC — 60 seconds

Open **Workspace Settings**:

- Show the four members and role guide.
- Explain OWNER/ADMIN/MEMBER/VIEWER capabilities.
- Point out role selection, member removal confirmation, and workspace rename/delete controls.
- Do not remove the demo owner or delete the seed workspace.

Optional: sign in as the engineer in a private browser window to show that project/AI-plan/member administration is restricted while task editing remains available.

### 4. Project and deterministic dependency risk — 2 minutes

Open **Projects**, then **Placement Preparation Platform** tasks.

Show the nine seeded tasks:

1. Design Platform Architecture
2. Build Authentication
3. Create Resume Builder
4. Implement Job Tracker
5. Build Placement Dashboard
6. Add Interview Preparation
7. Integrate Notifications
8. Write Test Cases
9. Deploy Application

Open **Create Resume Builder**:

- Show its dependency on **Build Authentication**.
- Show `AT RISK` and the explicit reason that authentication is blocked.
- Explain that the reason comes from deterministic backend rules, not an AI guess.
- Mention self-dependency/cycle rejection and same-workspace validation.

Optional interaction: change authentication to `DONE` in another tab and refresh resume-builder risk. Avoid changing demo state if you want the blocked example for a later audience.

### 5. Task list and Kanban — 45 seconds

- Filter by project, status, priority, risk, and assignee.
- Switch between list and Kanban.
- Drag a noncritical task between columns (or use its keyboard drag handle) and show the optimistic update and success toast.
- Explain that OWNER/ADMIN can delete tasks; MEMBER can edit but not delete.

### 6. AI plan preview and approval — 2 minutes

Open **AI Plan Generator** and enter a brief such as:

> Plan a customer onboarding pilot with product, engineering, QA, and launch readiness.

Before generating, say:

> “Watch the project count: preview and approval are separate operations.”

- Generate the preview.
- Point to **AI suggestion — not saved yet**.
- Review proposed owners, dates, task keys, dependencies, risks, and assumptions.
- Explain strict output/reference/cycle validation.
- Approve explicitly and open the created project tasks.

Optional: open **Audit Activity** and identify proposal-created and proposal-approved events. Explain idempotent approval replay and transactional writes.

### 7. Meeting extraction with selected approval — 90 seconds

Open **Meeting Notes** and select **Placement preparation sync**, or create a short new note linked to Placement Preparation Platform.

- Extract actions.
- Emphasize that no tasks have been created yet.
- Select only one or two action items.
- Choose the project and approve the selected items.

Talking point:

> “Selected-key approval means the reviewer is not forced to accept the entire model response.”

### 8. Documents, search, and duplicates — 60 seconds

- Open **Documents** and show the Placement Preparation Platform Runbook and indexing status.
- Open **Search & Docs** and search `placement blockers` or `authentication readiness`.
- Explain pgvector ranking with PostgreSQL full-text fallback and SQLite test fallback.
- If duplicate suggestions are visible on the dashboard, dismiss one and note that dismissal never merges or deletes tasks automatically.

### 9. Audit and engineering evidence — 45 seconds

Open **Audit Activity**:

- Show pagination and workspace-scoped events.
- Explain that important authentication, workspace, project/task, AI, meeting, and document actions are recorded.
- Note there is no audit update/delete API.

Close with:

> “The repository includes backend unit/integration tests, focused React tests, five Playwright scenarios, and a CI workflow that runs the browser suite against Docker Compose with mock AI.”

## Architecture whiteboard answer

Draw or describe:

```text
React / TanStack Query
          │ JWT + workspace-scoped JSON
          ▼
       FastAPI ───────────────► AIProvider
          │                       ├─ Mock (default)
          │                       └─ Optional remote provider
          ├─► PostgreSQL + pgvector
          ├─► Redis ◄──► Celery worker
          └─► Audit records
```

Then explain the AI write boundary:

```text
Untrusted output → strict validation → PENDING proposal → human review
                                                         ├─ reject: status only
                                                         └─ approve: revalidate + transaction
```

## Likely interview questions

### “Why not let AI create tasks directly?”

Model output can be malformed, stale, or based on invalid owners/dependencies. A pending proposal separates untrusted generation from validated, authorized writes. Approval also creates a clear audit event and supports safe replay.

### “How do you prevent cross-tenant access?”

Membership dependencies guard every workspace route, resource queries include workspace IDs, and nested task/project/note/document lookups are scoped to the active workspace. E2E includes both foreign-workspace 403 and same-workspace/foreign-task 404 checks.

### “Is risk generated by AI?”

No. Risk uses deterministic statuses, dates, and dependency facts, and returns human-readable reasons. AI is used for assistive summaries/plans, not the risk rule engine.

### “Why use a mock provider?”

It makes development and CI deterministic, offline, and free. The provider interface preserves a replaceable boundary for plans, meeting actions, embeddings, and summaries. The optional remote provider has not been called during this project’s validation.

### “What would you improve next?”

Add bulk task risk/dependency reads, batch large embedding workloads, evaluate task embeddings, add production observability and load testing, and consider HttpOnly refresh cookies with CSRF protection. These are roadmap items, not current claims.

## Recovery during a live demo

- **AI unavailable:** explain safe 503 handling; project/task data remains usable. Mock mode should not require network access.
- **Embedding pending/failed:** source creation still succeeds; show status and worker logs without exposing secrets.
- **Permission denied:** use it as an RBAC demonstration, then return to the owner account.
- **Browser E2E unavailable:** show the five spec names and state clearly that discovery is not execution. Never claim a pass you did not observe.
- **Seed already modified:** rerun for missing records; note that idempotency deliberately preserves existing task state rather than resetting the demo.

## Claims to avoid

- Do not say the app is deployed, highly available, or load-tested.
- Do not claim real OpenAI calls, production-scale semantic quality, or E2E success unless you personally ran them.
- Do not expose seed passwords, JWTs, local tokens, `.env`, or backend stack traces.
