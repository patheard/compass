"""Authentication routes."""

from datetime import datetime, timezone
from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import RedirectResponse, HTMLResponse
from app.auth.config import auth_config
from app.auth.models import GoogleUserInfo
from app.database.models.users import User
from app.auth.oauth import google_oauth
from app.localization import (
    configure_jinja_i18n,
    get_user_preferred_language,
    get_translation_function,
)


def get_localized_template_response(
    request: Request, template_name: str, context: dict
) -> HTMLResponse:
    """Get a template response with proper localization configured."""
    from fastapi.templating import Jinja2Templates

    # Create templates instance
    templates = Jinja2Templates(directory="./app/templates")

    # Get user's preferred language
    accept_language = request.headers.get("accept-language", "")
    language = get_user_preferred_language(accept_language)

    # Configure localization
    configure_jinja_i18n(templates.env, language)

    # Get translation function
    _ = get_translation_function(language)

    # Update context with translation function if title needs translation
    if context.get("title") == "Welcome to Compass":
        context["title"] = _("welcome_title")

    return templates.TemplateResponse(template_name, context)


router = APIRouter(prefix="/auth", tags=["authentication"])


@router.get("/login")
async def login(request: Request) -> RedirectResponse:
    """Initiate Google OAuth login."""
    auth_config.validate_config()

    redirect_uri = f"{auth_config.BASE_URL}/auth/callback"
    return await google_oauth.get_client().authorize_redirect(request, redirect_uri)


@router.get("/callback")
async def callback(request: Request) -> RedirectResponse:
    """Handle Google OAuth callback."""
    try:
        # Get token from Google
        token = await google_oauth.get_client().authorize_access_token(request)

        # Get user info from Google
        user_info_dict = token.get("userinfo")
        if not user_info_dict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get user information from Google",
            )

        # Create user object
        user_info = GoogleUserInfo(**user_info_dict)

        # Get or create user in database
        user = User.get_by_google_id(user_info.sub)
        if user:
            # Update existing user's last login
            user.update_last_login()
        else:
            # Create new user
            user = User.create_user(
                google_id=user_info.sub,
                email=user_info.email,
                name=user_info.name,
                last_login=datetime.now(timezone.utc),
            )

        # Store user in session (convert to dict for session storage)
        request.session["user"] = user.to_dict()

        # Redirect to home page after successful login
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication failed: {str(e)}",
        )


@router.get("/logout")
async def logout(request: Request) -> RedirectResponse:
    """Logout user and clear session."""
    request.session.clear()
    # Redirect to home page after logout
    return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
