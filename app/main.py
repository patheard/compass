"""Main FastAPI application module."""

from fastapi import FastAPI, Request, Depends
from fastapi.templating import Jinja2Templates
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
    RateLimitMiddleware, 
    InputValidationMiddleware
)
from app.security.session import session_config
from app.security.cors import cors_config

app = FastAPI(
    title="Security Assessment Automation Platform",
    description="A platform for automating security assessments",
    version="1.0.0"
)

app.add_middleware(InputValidationMiddleware)

app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=60,
    burst_requests=10
)

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

templates = Jinja2Templates(directory="./app/templates")


@app.get("/", response_class=HTMLResponse)
async def welcome(
    request: Request, 
    current_user: Optional[User] = Depends(get_user_from_session)
) -> HTMLResponse:
    """Render the welcome page."""
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request, 
            "title": "Welcome to SAAP",
            "user": current_user
        }
    )


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}
