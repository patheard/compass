"""Main FastAPI application module."""

from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from typing import Optional
from app.auth.routes import router as auth_router
from app.auth.middleware import get_user_from_session
from app.auth.models import User
from app.auth.config import auth_config
from app.security.middleware import (
    SecurityHeadersMiddleware, 
    InputValidationMiddleware
)
from app.security.session import session_config
from app.security.cors import cors_config
from app.template_utils import LocalizedTemplates

app = FastAPI(
    title="Compass",
    description="A platform for automating security assessments",
    version="1.0.0"
)

app.add_middleware(InputValidationMiddleware)

app.add_middleware(
    SecurityHeadersMiddleware,
    enforce_https=True,
    max_age=31536000,  # 1 year HSTS
    include_subdomains=True
)

app.add_middleware(CORSMiddleware, **cors_config.get_cors_kwargs())

app.add_middleware(
    SessionMiddleware, 
    **session_config.get_session_middleware_kwargs()
)

# Include authentication routes
app.include_router(auth_router)

templates = LocalizedTemplates(directory="./app/templates")


@app.get("/", response_class=HTMLResponse)
async def welcome(
    request: Request, 
    current_user: Optional[User] = Depends(get_user_from_session)
) -> HTMLResponse:
    """Render the welcome page."""
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "request": request, 
            "title": "welcome_title",  # Will be translated automatically in template
            "user": current_user
        }
    )


@app.get("/fr", response_class=HTMLResponse)
async def welcome_french(
    request: Request, 
    current_user: Optional[User] = Depends(get_user_from_session)
) -> HTMLResponse:
    """Render the welcome page in French."""
    from app.localization import configure_jinja_i18n
    
    # Force French localization
    configure_jinja_i18n(templates.templates.env, 'fr')
    
    return templates.templates.TemplateResponse(
        "index.html",
        {
            "request": request, 
            "title": "welcome_title",  # Will be translated automatically in template
            "user": current_user
        }
    )


@app.get("/security", response_class=HTMLResponse)
async def security_page(
    request: Request, 
    current_user: Optional[User] = Depends(get_user_from_session)
) -> HTMLResponse:
    """Render the security assessment page with custom content."""
    return templates.TemplateResponse(
        request,
        "security.html",
        {
            "request": request, 
            "title": "security_assessment",  # Will be translated automatically in template
            "user": current_user
        }
    )


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}
