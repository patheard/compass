"""Main FastAPI application module."""

from fastapi import FastAPI, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from starlette.middleware.sessions import SessionMiddleware
from typing import Optional
from app.auth.routes import router as auth_router
from app.auth.middleware import get_user_from_session
from app.auth.models import User
from app.auth.config import auth_config

app = FastAPI(
    title="Security Assessment Automation Platform",
    description="A platform for automating security assessments",
    version="1.0.0"
)

# Add session middleware for OAuth state management
app.add_middleware(
    SessionMiddleware, 
    secret_key=auth_config.SECRET_KEY
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
