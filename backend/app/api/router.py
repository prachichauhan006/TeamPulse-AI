from fastapi import APIRouter

from app.api.routes import ai, audit_logs, auth, documents, meeting_notes, projects, search, tasks, workspaces

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(workspaces.router)
api_router.include_router(projects.router)
api_router.include_router(tasks.router)
api_router.include_router(audit_logs.router)
api_router.include_router(ai.router)
api_router.include_router(meeting_notes.router)
api_router.include_router(documents.router)
api_router.include_router(search.router)
