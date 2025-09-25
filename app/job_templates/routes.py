"""Routes for job template management."""

import ast
import json
from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import UUID4

from app.auth.middleware import require_authenticated_user
from app.database.models.users import User
from app.job_templates.services import JobTemplateService
from app.templates.utils import LocalizedTemplates
from app.assessments.base import CSRFTokenManager

router = APIRouter(prefix="/job-templates", tags=["job-templates"])
templates = LocalizedTemplates(directory="./app/templates")
csrf_manager = CSRFTokenManager()


@router.get("", response_class=HTMLResponse)
async def list_templates(
    request: Request,
    current_user: User = Depends(require_authenticated_user),
) -> HTMLResponse:
    """Get all job templates in the system."""
    try:
        templates_data = JobTemplateService.get_all_templates()

        # Generate CSRF token for delete functionality
        csrf_token = csrf_manager.generate_csrf_token()
        request.session["csrf_token"] = csrf_token

        # Convert templates for display
        serialized_templates = []
        for template in templates_data:
            serialized_templates.append(
                {
                    "template_id": template.template_id,
                    "name": template.name,
                    "description": template.description,
                    "scan_type": template.scan_type,
                    "is_active": template.is_active,
                    "created_at": getattr(template, "created_at", None),
                    "updated_at": getattr(template, "updated_at", None),
                }
            )

        return templates.TemplateResponse(
            request,
            "pages/job_templates/list.html",
            {
                "title": "Job templates",
                "request": request,
                "templates": serialized_templates,
                "user": current_user,
                "csrf_token": csrf_token,
                "breadcrumbs": [
                    {"label": "Compass", "link": "/"},
                ],
            },
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/new", response_class=HTMLResponse)
async def create_template_form(
    request: Request,
    current_user: User = Depends(require_authenticated_user),
) -> HTMLResponse:
    """Show form to create a new job template."""
    # Generate CSRF token for form
    csrf_token = csrf_manager.generate_csrf_token()
    request.session["csrf_token"] = csrf_token

    scan_types = ["aws_config"]
    return templates.TemplateResponse(
        request,
        "pages/job_templates/form.html",
        {
            "title": "Create template",
            "request": request,
            "scan_types": scan_types,
            "user": current_user,
            "csrf_token": csrf_token,
            "breadcrumbs": [
                {"label": "Compass", "link": "/"},
            ],
        },
    )


@router.post("/new", response_class=HTMLResponse)
async def create_template(
    request: Request,
    name: str = Form(...),
    description: str = Form(...),
    scan_type: str = Form(...),
    config: str = Form(...),
    csrf_token: str = Form(...),
    current_user: User = Depends(require_authenticated_user),
) -> RedirectResponse:
    """Create a new scan job template."""
    # Validate CSRF token
    session_token = request.session.get("csrf_token")
    if not csrf_manager.validate_csrf_token(session_token, csrf_token):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")

    try:
        # Parse JSON config
        try:
            config_dict = ast.literal_eval(config)
        except (ValueError, SyntaxError) as e:
            raise HTTPException(
                status_code=400, detail=f"Invalid JSON configuration: {e}"
            )

        template = JobTemplateService.create_template(
            name=name,
            description=description,
            scan_type=scan_type,
            config=config_dict,
        )

        print(f"Created template: {template}")

        # Clear CSRF token
        request.session.pop("csrf_token", None)

        return RedirectResponse(
            url=f"/job-templates/{template.template_id}",
            status_code=303,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{template_id}", response_class=HTMLResponse)
async def get_template(
    request: Request,
    template_id: UUID4,
    current_user: User = Depends(require_authenticated_user),
) -> HTMLResponse:
    """Get a specific scan job template."""
    try:
        template = JobTemplateService.get_template(str(template_id))
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        # Generate CSRF token for form
        csrf_token = csrf_manager.generate_csrf_token()
        request.session["csrf_token"] = csrf_token

        # Convert config to JSON string for template display
        template_data = {
            "template_id": template.template_id,
            "name": template.name,
            "description": template.description,
            "scan_type": template.scan_type,
            "config": json.dumps(template.config.as_dict(), indent=2),
            "is_active": template.is_active,
            "created_at": getattr(template, "created_at", None),
            "updated_at": getattr(template, "updated_at", None),
        }

        return templates.TemplateResponse(
            request,
            "pages/job_templates/detail.html",
            {
                "title": "Job template details",
                "request": request,
                "template": template_data,
                "user": current_user,
                "csrf_token": csrf_token,
                "breadcrumbs": [
                    {"label": "Compass", "link": "/"},
                    {
                        "label": "Job templates",
                        "link": "/job-templates",
                    },
                ],
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{template_id}/edit", response_class=HTMLResponse)
async def edit_template_form(
    request: Request,
    template_id: UUID4,
    current_user: User = Depends(require_authenticated_user),
) -> HTMLResponse:
    """Show form to edit a scan job template."""
    try:
        template = JobTemplateService.get_template(str(template_id))
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        # Generate CSRF token for form
        csrf_token = csrf_manager.generate_csrf_token()
        request.session["csrf_token"] = csrf_token

        scan_types = ["aws_config"]

        # Convert config to JSON string for form display
        template_data = {
            "template_id": template.template_id,
            "name": template.name,
            "description": template.description,
            "scan_type": template.scan_type,
            "config": template.config.as_dict(),
            "is_active": template.is_active,
        }

        return templates.TemplateResponse(
            request,
            "pages/job_templates/form.html",
            {
                "title": "Edit job template",
                "request": request,
                "template": template_data,
                "scan_types": scan_types,
                "user": current_user,
                "csrf_token": csrf_token,
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{template_id}/edit", response_class=HTMLResponse)
async def update_template(
    request: Request,
    template_id: UUID4,
    name: str = Form(...),
    description: str = Form(...),
    scan_type: str = Form(...),
    config: str = Form(...),
    csrf_token: str = Form(...),
    current_user: User = Depends(require_authenticated_user),
) -> RedirectResponse:
    """Update a scan job template."""
    # Validate CSRF token
    session_token = request.session.get("csrf_token")
    if not csrf_manager.validate_csrf_token(session_token, csrf_token):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")

    try:
        # Parse JSON config
        try:
            config_dict = ast.literal_eval(config)
        except (ValueError, SyntaxError) as e:
            raise HTTPException(
                status_code=400, detail=f"Invalid JSON configuration: {e}"
            )

        template = JobTemplateService.update_template(
            template_id=str(template_id),
            name=name,
            description=description,
            scan_type=scan_type,
            config=config_dict,
        )
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        # Clear CSRF token
        request.session.pop("csrf_token", None)

        return RedirectResponse(
            url=f"/job-templates/{template.template_id}",
            status_code=303,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{template_id}/delete")
async def delete_template(
    template_id: UUID4,
    request: Request,
    csrf_token: str = Form(...),
    current_user: User = Depends(require_authenticated_user),
) -> RedirectResponse:
    """Delete (deactivate) a scan job template."""
    # Validate CSRF token
    session_token = request.session.get("csrf_token")
    if not csrf_manager.validate_csrf_token(session_token, csrf_token):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")

    try:
        JobTemplateService.delete_template(str(template_id))

        # Clear CSRF token
        request.session.pop("csrf_token", None)

        return RedirectResponse(
            url="/job-templates",
            status_code=303,
        )

    except HTTPException as e:
        if e.status_code == 404:
            raise HTTPException(status_code=404, detail="Template not found")
        raise
