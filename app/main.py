"""Main FastAPI application module."""

from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from starlette.middleware.sessions import SessionMiddleware
from typing import Optional
from app.auth.routes import router as auth_router
from app.auth.middleware import get_user_from_session
from app.auth.models import User
from app.security.middleware import SecurityHeadersMiddleware
from app.security.session import session_config
from app.security.cors import cors_config
from app.localization.middleware import LocalizationMiddleware
from app.localization.utils import LANGUAGES
from app.templates.utils import LocalizedTemplates

app = FastAPI(
    title="Compass",
    description="A platform for automating security assessments",
    version="1.0.0",
)
handler = Mangum(app)

# Middleware
app.add_middleware(
    SecurityHeadersMiddleware,
    enforce_https=True,
    max_age=31536000,  # 1 year HSTS
    include_subdomains=True,
)
app.add_middleware(CORSMiddleware, **cors_config.get_cors_kwargs())
app.add_middleware(LocalizationMiddleware)
app.add_middleware(SessionMiddleware, **session_config.get_session_middleware_kwargs())

# Routes
app.include_router(auth_router)

# Templates
templates = LocalizedTemplates(directory="./app/templates")


@app.get("/", response_class=HTMLResponse)
async def root(
    request: Request, current_user: Optional[User] = Depends(get_user_from_session)
) -> HTMLResponse:
    """Route users to appropriate page based on session status."""
    if current_user:
        # Authenticated user - show home page
        return templates.TemplateResponse(
            request,
            "pages/home.html",
            {"request": request, "title": "welcome_title", "user": current_user},
        )
    else:
        # Unauthenticated user - show login page
        return templates.TemplateResponse(
            request,
            "pages/login.html",
            {"request": request, "title": "welcome_title", "user": None},
        )


@app.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request, current_user: Optional[User] = Depends(get_user_from_session)
) -> HTMLResponse:
    """Render the login page."""
    return templates.TemplateResponse(
        request,
        "pages/login.html",
        {"request": request, "title": "login_title", "user": current_user},
    )


@app.get("/home", response_class=HTMLResponse)
async def home_page(
    request: Request, current_user: Optional[User] = Depends(get_user_from_session)
) -> HTMLResponse:
    """Render the home page."""
    return templates.TemplateResponse(
        request,
        "pages/home.html",
        {"request": request, "title": "welcome_title", "user": current_user},
    )


@app.get("/lang/{language}")
async def set_language(
    language: str,
    request: Request,
    current_user: Optional[User] = Depends(get_user_from_session),
) -> RedirectResponse:
    """Set user's preferred language."""
    if language not in LANGUAGES:
        raise HTTPException(status_code=400, detail="Unsupported language")

    request.session["preferred_language"] = language

    referrer = request.headers.get("referer", "/")
    return RedirectResponse(url=referrer, status_code=302)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}
