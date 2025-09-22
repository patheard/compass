"""Routes for scan job template management."""

import ast
from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import UUID4

from app.auth.middleware import require_authenticated_user
from app.database.models.users import User
from app.scan_job_templates.services import ScanJobTemplateService
from app.templates.utils import LocalizedTemplates
from app.assessments.base import CSRFTokenManager

router = APIRouter(prefix="/jobs", tags=["scan-job-templates"])
templates = LocalizedTemplates(directory="./app/templates")
csrf_manager = CSRFTokenManager()


@router.get("/", response_class=HTMLResponse)
async def list_templates(
    request: Request,
    current_user: User = Depends(require_authenticated_user),
) -> HTMLResponse:
    """Get all scan job templates in the system."""
    try:
        templates_data = ScanJobTemplateService.get_all_templates()

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
            "pages/jobs/list.html",
            {
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
    """Show form to create a new scan job template."""
    # Generate CSRF token for form
    csrf_token = csrf_manager.generate_csrf_token()
    request.session["csrf_token"] = csrf_token

    scan_types = ["aws_config"]
    return templates.TemplateResponse(
        request,
        "pages/jobs/form.html",
        {
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
) -> HTMLResponse:
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

        template = ScanJobTemplateService.create_template(
            name=name,
            description=description,
            scan_type=scan_type,
            config=config_dict,
        )

        print(f"Created template: {template}")

        # Clear CSRF token
        request.session.pop("csrf_token", None)

        # Convert config to JSON string for template display
        template_data = {
            "template_id": template.template_id,
            "name": template.name,
            "description": template.description,
            "scan_type": template.scan_type,
            "config": template.config.as_dict(),
            "is_active": template.is_active,
            "created_at": getattr(template, "created_at", None),
            "updated_at": getattr(template, "updated_at", None),
        }

        return templates.TemplateResponse(
            request,
            "pages/jobs/detail.html",
            {"request": request, "template": template_data, "user": current_user},
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
        template = ScanJobTemplateService.get_template(str(template_id))
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
            "config": template.config.as_dict(),
            "is_active": template.is_active,
            "created_at": getattr(template, "created_at", None),
            "updated_at": getattr(template, "updated_at", None),
        }

        return templates.TemplateResponse(
            request,
            "pages/jobs/detail.html",
            {
                "request": request,
                "template": template_data,
                "user": current_user,
                "csrf_token": csrf_token,
                "breadcrumbs": [
                    {"label": "Compass", "link": "/"},
                    {
                        "label": "Jobs",
                        "link": "/jobs",
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
        template = ScanJobTemplateService.get_template(str(template_id))
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
            "pages/jobs/form.html",
            {
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
) -> HTMLResponse:
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

        template = ScanJobTemplateService.update_template(
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

        # Convert config to JSON string for template display
        template_data = {
            "template_id": template.template_id,
            "name": template.name,
            "description": template.description,
            "scan_type": template.scan_type,
            "config": template.config.as_dict(),
            "is_active": template.is_active,
            "created_at": getattr(template, "created_at", None),
            "updated_at": getattr(template, "updated_at", None),
        }

        return templates.TemplateResponse(
            request,
            "pages/jobs/detail.html",
            {"request": request, "template": template_data, "user": current_user},
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
        ScanJobTemplateService.delete_template(str(template_id))

        # Clear CSRF token
        request.session.pop("csrf_token", None)

        return RedirectResponse(
            url="/jobs",
            status_code=303,
        )

    except HTTPException as e:
        if e.status_code == 404:
            raise HTTPException(status_code=404, detail="Template not found")
        raise
