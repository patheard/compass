"""Authentication models."""

from pydantic import BaseModel, EmailStr


class GoogleUserInfo(BaseModel):
    """Google user information from OAuth."""

    email: EmailStr
    name: str
    picture: str | None = None
    sub: str  # Google ID
    email_verified: bool
