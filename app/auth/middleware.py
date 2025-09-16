"""Authentication middleware and dependencies."""

from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.auth.models import User, TokenData
from app.auth.oauth import jwt_handler


security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[User]:
    """Get current authenticated user from JWT token."""
    if not credentials:
        return None
    
    try:
        token_data: TokenData = jwt_handler.verify_token(credentials.credentials)
        if token_data.email is None or token_data.google_id is None:
            return None
        
        # In a real app, you would fetch user from database
        # For now, return a user object from token data
        user = User(
            email=token_data.email,
            name=token_data.email.split("@")[0],  # Simple name extraction
            google_id=token_data.google_id
        )
        return user
    except HTTPException:
        return None


async def require_auth(
    current_user: Optional[User] = Depends(get_current_user)
) -> User:
    """Require authentication - raise exception if not authenticated."""
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user


async def get_user_from_session(request: Request) -> Optional[User]:
    """Get user from session cookie (fallback to session-based auth)."""
    user_data = request.session.get("user")
    if not user_data:
        return None
    
    try:
        return User(**user_data)
    except Exception:
        return None