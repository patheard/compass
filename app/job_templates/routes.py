"""Routes for job template management."""

import json
from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import UUID4

from app.auth.middleware import require_authenticated_user
from app.constants import AWS_RESOURCES, NIST_CONTROL_IDS
from app.database.models.users import User
from app.job_templates.services import JobTemplateService
from app.templates.utils import LocalizedTemplates
from app.assessments.base import CSRFTokenManager, format_validation_error
from app.job_templates.validation import JobTemplateRequest

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
            "aws_resources": AWS_RESOURCES,
            "nist_control_ids": NIST_CONTROL_IDS,
            "breadcrumbs": [
                {"label": "Compass", "link": "/"},
                {"label": "Job templates", "link": "/job-templates"},
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
    aws_resources: str = Form("[]"),
    nist_control_ids: str = Form("[]"),
    csrf_token: str = Form(...),
    current_user: User = Depends(require_authenticated_user),
) -> RedirectResponse:
    """Create a new scan job template."""
    # Validate CSRF token
    session_token = request.session.get("csrf_token")
    if not csrf_manager.validate_csrf_token(session_token, csrf_token):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")

    try:
        # Parse aws_resources from JSON string
        try:
            aws_resources_list = json.loads(aws_resources) if aws_resources else []
        except json.JSONDecodeError:
            aws_resources_list = []

        # Parse nist_control_ids from JSON string
        try:
            nist_control_ids_list = (
                json.loads(nist_control_ids) if nist_control_ids else []
            )
        except json.JSONDecodeError:
            nist_control_ids_list = []

        data = JobTemplateRequest(
            name=name,
            description=description,
            scan_type=scan_type,
            config=config,
            aws_resources=aws_resources_list if aws_resources_list else None,
            nist_control_ids=nist_control_ids_list if nist_control_ids_list else None,
        )

        template = JobTemplateService.create_template(data)

        request.session.pop("csrf_token", None)

        return RedirectResponse(
            url=f"/job-templates/{template.template_id}",
            status_code=303,
        )
    except ValueError as e:
        csrf_token = csrf_manager.generate_csrf_token()
        request.session["csrf_token"] = csrf_token

        # Parse aws_resources for error display
        try:
            aws_resources_list = json.loads(aws_resources) if aws_resources else []
        except json.JSONDecodeError:
            aws_resources_list = []

        # Parse nist_control_ids for error display
        try:
            nist_control_ids_list = (
                json.loads(nist_control_ids) if nist_control_ids else []
            )
        except json.JSONDecodeError:
            nist_control_ids_list = []

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
                "error": format_validation_error(e),
                "name": name,
                "description": description,
                "scan_type": scan_type,
                "config": config,
                "selected_aws_resources": aws_resources_list,
                "aws_resources": AWS_RESOURCES,
                "selected_nist_control_ids": nist_control_ids_list,
                "nist_control_ids": NIST_CONTROL_IDS,
                "breadcrumbs": [
                    {"label": "Compass", "link": "/"},
                ],
            },
        )
    except HTTPException:
        raise
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
            "aws_resources": template.aws_resources,
            "nist_control_ids": template.nist_control_ids,
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
            "aws_resources": template.aws_resources,
            "nist_control_ids": template.nist_control_ids,
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
                "aws_resources": AWS_RESOURCES,
                "nist_control_ids": NIST_CONTROL_IDS,
                "breadcrumbs": [
                    {"label": "Compass", "link": "/"},
                    {
                        "label": "Job templates",
                        "link": "/job-templates",
                    },
                    {
                        "label": template.name,
                        "link": f"/job-templates/{template.template_id}",
                    },
                ],
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
    aws_resources: str = Form("[]"),
    nist_control_ids: str = Form("[]"),
    csrf_token: str = Form(...),
    current_user: User = Depends(require_authenticated_user),
) -> RedirectResponse:
    """Update a scan job template."""
    # Validate CSRF token
    session_token = request.session.get("csrf_token")
    if not csrf_manager.validate_csrf_token(session_token, csrf_token):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")

    try:
        # Parse aws_resources from JSON string
        try:
            aws_resources_list = json.loads(aws_resources) if aws_resources else []
        except json.JSONDecodeError:
            aws_resources_list = []

        # Parse nist_control_ids from JSON string
        try:
            nist_control_ids_list = (
                json.loads(nist_control_ids) if nist_control_ids else []
            )
        except json.JSONDecodeError:
            nist_control_ids_list = []

        data = JobTemplateRequest(
            name=name,
            description=description,
            scan_type=scan_type,
            config=config,
            aws_resources=aws_resources_list if aws_resources_list else None,
            nist_control_ids=nist_control_ids_list if nist_control_ids_list else None,
        )

        template = JobTemplateService.update_template(
            template_id=str(template_id), data=data
        )
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        request.session.pop("csrf_token", None)

        return RedirectResponse(
            url=f"/job-templates/{template.template_id}",
            status_code=303,
        )

    except ValueError as e:
        csrf_token = csrf_manager.generate_csrf_token()
        request.session["csrf_token"] = csrf_token

        # Parse aws_resources for error display
        try:
            aws_resources_list = json.loads(aws_resources) if aws_resources else []
        except json.JSONDecodeError:
            aws_resources_list = []

        # Parse nist_control_ids for error display
        try:
            nist_control_ids_list = (
                json.loads(nist_control_ids) if nist_control_ids else []
            )
        except json.JSONDecodeError:
            nist_control_ids_list = []

        scan_types = ["aws_config"]
        # Re-display the form with previously-entered values and the error
        return templates.TemplateResponse(
            request,
            "pages/job_templates/form.html",
            {
                "title": "Edit job template",
                "request": request,
                "template": {
                    "template_id": str(template_id),
                    "name": name,
                    "description": description,
                    "scan_type": scan_type,
                    "config": config,
                    "is_active": True,
                    "aws_resources": aws_resources_list,
                    "nist_control_ids": nist_control_ids_list,
                },
                "scan_types": scan_types,
                "user": current_user,
                "csrf_token": csrf_token,
                "error": format_validation_error(e),
                "aws_resources": AWS_RESOURCES,
                "nist_control_ids": NIST_CONTROL_IDS,
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
