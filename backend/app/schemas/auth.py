import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.common import ORMModel


def validate_password_strength(value: str) -> str:
    if len(value) < 12 or len(value) > 128:
        raise ValueError("Password must contain between 12 and 128 characters")
    if not any(character.isalpha() for character in value):
        raise ValueError("Password must contain at least one letter")
    if not any(character.isdigit() for character in value):
        raise ValueError("Password must contain at least one number")
    return value


class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=120)
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return validate_password_strength(value)

    @field_validator("full_name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Full name cannot be blank")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1, max_length=4096)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=1, max_length=4096)


class UserResponse(ORMModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    is_active: bool
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
