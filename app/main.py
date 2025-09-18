"""Main FastAPI application module."""

import logging
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from starlette.middleware.sessions import SessionMiddleware
from typing import Optional
from app.auth.routes import router as auth_router
from app.assessments.routes import router as assessment_router
from app.assessments.services import AssessmentService
from app.controls.routes import router as control_router
from app.evidence.routes import router as evidence_router
from app.auth.middleware import get_user_from_session
from app.database.models.users import User
from app.security.middleware import SecurityHeadersMiddleware
from app.security.session import session_config
from app.security.cors import cors_config
from app.localization.middleware import LocalizationMiddleware
from app.localization.utils import LANGUAGES
from app.templates.utils import LocalizedTemplates
from app.database import DatabaseManager


logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Compass",
    description="A platform for automating security assessments",
    version="1.0.0",
)
handler = Mangum(app)


#
# TODO: Come up with a less hacky way to do this or just assume the tables will exist
# in the expected state because they're managed in Terraform.
#
@app.on_event("startup")
async def startup_event() -> None:
    """Initialize database tables on application startup."""
    try:
        logger.info("Initializing database tables...")
        success = DatabaseManager.initialize_tables()
        if success:
            logger.info("Database initialization completed successfully")
        else:
            logger.error("Database initialization completed with errors")
    except Exception as e:
        logger.error(f"Failed to initialize database tables: {e}")
        raise e


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
app.include_router(assessment_router)
app.include_router(control_router)
app.include_router(evidence_router)

# Static files
app.mount("/static", StaticFiles(directory="./app/static"), name="static")

templates = LocalizedTemplates(directory="./app/templates")
assessment_service = AssessmentService()


@app.get("/", response_class=HTMLResponse)
async def root(
    request: Request, current_user: Optional[User] = Depends(get_user_from_session)
) -> HTMLResponse:
    """Route users to appropriate page based on session status."""
    if current_user:
        # Authenticated user - show home page
        assessments = assessment_service.list_assessments(current_user.user_id)
        return templates.TemplateResponse(
            request,
            "pages/home.html",
            {
                "request": request,
                "title": "welcome_title",
                "user": current_user,
                "assessments": assessments,
            },
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
async def database_health_check() -> dict[str, object]:
    """Database health check endpoint."""
    is_healthy = False
    try:
        is_healthy = DatabaseManager.check_table_health()
    except Exception as e:
        logger.error(f"Database health check failed: {e}")

    if is_healthy:
        return {"status": "healthy"}
    else:
        raise HTTPException(
            status_code=503,
            detail={"status": "unhealthy"},
        )
