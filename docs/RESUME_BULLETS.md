# TeamPulse AI — Accurate Resume Bullets

Use only claims you can explain and demonstrate. These bullets describe implemented repository features; they do not claim deployment, scale, external-provider testing, or unexecuted E2E results.

## Full-stack project bullets

- Built **TeamPulse AI**, a multi-tenant team operations platform using **FastAPI, PostgreSQL, React, TypeScript, Vite, and Tailwind**, with workspace-scoped projects, tasks, documents, meeting notes, and audit history.
- Implemented authentication with **Argon2 password hashing, short-lived JWT access tokens, rotating hashed refresh tokens, logout revocation, and session-expired frontend handling**, plus IP/user rate limits and OWNER/ADMIN/MEMBER/VIEWER RBAC.
- Designed an **approval-gated AI workflow** with strict schema/reference/cycle validation, pending plan previews, selected meeting-action approval, transactional idempotent writes, and a deterministic offline provider for development and tests.
- Developed deterministic dependency-risk and project-health rules that surface **blocked, overdue, and upcoming dependency reasons**, with backend cycle prevention and role-aware task list/Kanban experiences.
- Implemented asynchronous document/meeting-note indexing with **Celery, Redis, 1536-dimensional pgvector embeddings, idempotent chunk replacement, and PostgreSQL full-text/SQLite fallbacks** for workspace-aware search.
- Created a responsive, accessible SaaS interface with **TanStack Query, protected routing, workspace switching, permission-restricted controls, loading/error/empty states, safe notifications, and destructive confirmations**.
- Added **55 passing backend tests and 7 passing frontend unit tests** in the build sandbox, strict TypeScript/Vite production build validation, and five authored Playwright scenarios for critical workflows and tenant isolation.
- Configured a **GitHub Actions CI workflow** for Ruff, pytest, frontend tests/build, and Docker Compose-backed Playwright execution using generated disposable settings and MockAIProvider without committed secrets.

## Concise two-bullet version

- Engineered a multi-tenant **FastAPI/React/PostgreSQL** team workspace with JWT session rotation, RBAC, dependency-aware Kanban tasks, audit logs, document search, and responsive TypeScript/Tailwind workflows.
- Built human-approved AI planning and meeting extraction with strict validation and transactional writes; added Celery/pgvector indexing, **55 backend + 7 frontend unit tests**, five Playwright scenarios, and Docker-backed CI configuration.

## Interview explanation for the test bullet

Say exactly what was observed:

> “In the development sandbox, 55 backend tests and 7 frontend unit tests passed, and the production frontend build succeeded. I also authored five Playwright scenarios and verified their discovery, but Docker/runtime services were unavailable there, so I do not claim those browser scenarios passed locally. CI is configured to run them with PostgreSQL, Redis, Celery, and mock AI.”

## Claims deliberately excluded

Do not add these unless you later perform and can evidence them:

- Production deployment, uptime, or real customer usage
- A specific number of supported users or performance improvement
- Load/penetration testing or a security certification
- Real OpenAI/ paid API integration testing
- Full browser E2E passage in the sandbox
- Production-quality semantic relevance from mock embeddings
- Microservice or hyperscale architecture
