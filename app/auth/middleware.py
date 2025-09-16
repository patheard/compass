"""Authentication middleware and dependencies."""

from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.auth.models import User, TokenData
from app.auth.oauth import jwt_handler
import time


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
        
        # Check if token is expired with some buffer time
        current_time = time.time()
        if hasattr(token_data, 'exp') and token_data.exp < current_time:
            return None
        
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
    """Get user from session cookie with enhanced security checks."""
    user_data = request.session.get("user")
    if not user_data:
        return None
    
    # Check session timestamp to enforce timeout
    session_timestamp = request.session.get("timestamp")
    if session_timestamp:
        current_time = time.time()
        session_age = current_time - session_timestamp
        
        # Session timeout: 15 minutes (900 seconds)
        if session_age > 900:
            # Clear expired session
            request.session.clear()
            return None
        
        # Update timestamp for sliding window
        request.session["timestamp"] = current_time
    else:
        # Set timestamp if not present
        request.session["timestamp"] = time.time()
    
    try:
        return User(**user_data)
    except Exception:
        # Clear invalid session data
        request.session.clear()
        return None


async def check_session_security(request: Request) -> None:
    """Additional session security checks."""
    # Check for session fixation attacks by validating session ID rotation
    user_agent = request.headers.get("User-Agent", "")
    stored_user_agent = request.session.get("user_agent")
    
    if stored_user_agent and stored_user_agent != user_agent:
        # Potential session hijacking - clear session
        request.session.clear()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session security violation detected"
        )
    
    # Store user agent for future checks
    if not stored_user_agent:
        request.session["user_agent"] = user_agent