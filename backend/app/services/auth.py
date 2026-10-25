from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token, create_refresh_token, hash_token
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import TokenResponse


def issue_token_pair(db: Session, user: User) -> TokenResponse:
    access_token = create_access_token(user.id)
    refresh_token, token_id, expires_at = create_refresh_token(user.id)
    db.add(
        RefreshToken(
            id=token_id,
            user_id=user.id,
            token_hash=hash_token(refresh_token),
            expires_at=expires_at,
        )
    )
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=get_settings().access_token_expire_minutes * 60,
    )
