import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.enums import WorkspaceRole
from app.schemas.common import ORMModel


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Workspace name cannot be blank")
        return value


class WorkspaceUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        return WorkspaceCreate.clean_name(value)


class WorkspaceDeleteRequest(BaseModel):
    confirmation: str = Field(min_length=1, max_length=120)


class WorkspaceResponse(ORMModel):
    id: uuid.UUID
    name: str
    created_at: datetime
    updated_at: datetime


class MemberAddRequest(BaseModel):
    email: EmailStr
    role: WorkspaceRole = WorkspaceRole.MEMBER


class MemberRoleUpdate(BaseModel):
    role: WorkspaceRole


class WorkspaceMemberResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    user_id: uuid.UUID
    email: EmailStr
    full_name: str
    role: WorkspaceRole
    created_at: datetime
    updated_at: datetime


class WorkspaceMemberListResponse(BaseModel):
    items: list[WorkspaceMemberResponse]
    total: int
