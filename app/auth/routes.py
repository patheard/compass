"""Authentication routes."""

from datetime import datetime, timezone
from fastapi import APIRouter, Request, HTTPException, status, Depends
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from app.auth.config import auth_config
from app.auth.models import User, Token, GoogleUserInfo
from app.auth.oauth import google_oauth, jwt_handler
from app.auth.middleware import get_current_user, get_user_from_session

templates = Jinja2Templates(directory="./app/templates")


router = APIRouter(prefix="/auth", tags=["authentication"])


@router.get("/login")
async def login(request: Request) -> RedirectResponse:
    """Initiate Google OAuth login."""
    auth_config.validate_config()
    
    redirect_uri = f"{auth_config.BASE_URL}/auth/callback"
    return await google_oauth.get_client().authorize_redirect(request, redirect_uri)


@router.get("/callback")
async def callback(request: Request) -> HTMLResponse:
    """Handle Google OAuth callback."""
    try:
        # Get token from Google
        token = await google_oauth.get_client().authorize_access_token(request)
        
        # Get user info from Google
        user_info_dict = token.get("userinfo")
        if not user_info_dict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get user information from Google"
            )
        
        # Create user object
        user_info = GoogleUserInfo(**user_info_dict)
        user = User(
            email=user_info.email,
            name=user_info.name,
            picture=user_info.picture,
            google_id=user_info.sub,
            last_login=datetime.now(timezone.utc)
        )

        # Store user in session
        request.session["user"] = user.model_dump(mode="json")
        
        # Return the index template with user data
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "title": "Welcome to Compass",
                "user": user
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication failed: {str(e)}"
        )


@router.post("/token")
async def get_token(
    current_user: User = Depends(get_user_from_session)
) -> Token:
    """Get JWT token for authenticated user."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated"
        )
    
    return jwt_handler.create_token_for_user(current_user)


@router.get("/logout")
async def logout(request: Request) -> HTMLResponse:
    """Logout user and clear session."""
    request.session.clear()
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "title": "Welcome to Compass",
            "user": None
        }
    )