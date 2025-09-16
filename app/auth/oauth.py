"""OAuth handlers for Google authentication."""

from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import HTTPException, status
from authlib.integrations.starlette_client import OAuth
from jose import JWTError, jwt
from app.auth.config import auth_config
from app.auth.models import Token, TokenData, User, GoogleUserInfo


class GoogleOAuth:
    """Google OAuth handler."""
    
    def __init__(self) -> None:
        """Initialize OAuth client."""
        self.oauth = OAuth()
        self.oauth.register(
            name="google",
            client_id=auth_config.GOOGLE_CLIENT_ID,
            client_secret=auth_config.GOOGLE_CLIENT_SECRET,
            server_metadata_url=auth_config.GOOGLE_DISCOVERY_URL,
            client_kwargs={
                "scope": "openid email profile",
            },
        )
    
    def get_client(self) -> OAuth:
        """Get OAuth client."""
        return self.oauth.google


class JWTHandler:
    """JWT token handler."""
    
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=auth_config.ACCESS_TOKEN_EXPIRE_MINUTES
            )
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(
            to_encode, auth_config.SECRET_KEY, algorithm=auth_config.ALGORITHM
        )
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> TokenData:
        """Verify JWT token and return token data."""
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(
                token, auth_config.SECRET_KEY, algorithms=[auth_config.ALGORITHM]
            )
            email: str = payload.get("sub")
            google_id: str = payload.get("google_id")
            if email is None or google_id is None:
                raise credentials_exception
            token_data = TokenData(email=email, google_id=google_id)
        except JWTError:
            raise credentials_exception
        return token_data
    
    @staticmethod
    def create_token_for_user(user: User) -> Token:
        """Create JWT token for authenticated user."""
        access_token_expires = timedelta(minutes=auth_config.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = JWTHandler.create_access_token(
            data={"sub": user.email, "google_id": user.google_id},
            expires_delta=access_token_expires
        )
        return Token(
            access_token=access_token,
            expires_in=auth_config.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )


# Singleton instances
google_oauth = GoogleOAuth()
jwt_handler = JWTHandler()