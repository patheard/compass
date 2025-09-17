"""Authentication models."""

from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, EmailStr


class User(BaseModel):
    """User model."""

    email: EmailStr
    name: str
    picture: Optional[str] = None
    google_id: str
    created_at: datetime = datetime.now(timezone.utc)
    last_login: Optional[datetime] = None


class Token(BaseModel):
    """JWT token model."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    """Token data for JWT payload."""

    email: Optional[str] = None
    google_id: Optional[str] = None


class GoogleUserInfo(BaseModel):
    """Google user information from OAuth."""

    email: EmailStr
    name: str
    picture: Optional[str] = None
    sub: str  # Google ID
    email_verified: bool
