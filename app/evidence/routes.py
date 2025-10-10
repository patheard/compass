"""Evidence routes for web interface and API endpoints."""

import logging
from typing import Optional
from fastapi import APIRouter, Request, Depends, Form, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from app.auth.middleware import require_authenticated_user
from app.database.models.users import User
from app.templates.utils import LocalizedTemplates
from app.evidence.services import EvidenceService
from app.evidence.services import S3Service
from app.evidence.validation import EvidenceRequest
from app.job_templates.services import JobTemplateService
from app.job_executions.services import JobExecutionService
from app.assessments.base import CSRFTokenManager, format_validation_error

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/assessments/{assessment_id}/controls/{control_id}/evidence",
    tags=["evidence"],
)
templates = LocalizedTemplates(directory="./app/templates")
evidence_service = EvidenceService()
s3_service = S3Service()
csrf_manager = CSRFTokenManager()


@router.get("/new", response_class=HTMLResponse)
async def create_evidence_page(
    assessment_id: str,
    control_id: str,
    request: Request,
    current_user: User = Depends(require_authenticated_user),
) -> HTMLResponse:
    """Display form to create new evidence."""
    try:
        # Get control and assessment info for context
        control, assessment = evidence_service.get_control_and_assessment_info(
            control_id, current_user.user_id
        )

        # Verify assessment ID matches
        if assessment.assessment_id != assessment_id:
            raise HTTPException(
                status_code=404, detail="Control not found in assessment"
            )

        # Generate CSRF token for form
        csrf_token = csrf_manager.generate_csrf_token()
        request.session["csrf_token"] = csrf_token

        # Get scan job templates for user
        job_templates = JobTemplateService.get_active_templates()

        return templates.TemplateResponse(
            request,
            "pages/evidence/form.html",
            {
                "request": request,
                "title": "Create evidence",
                "user": current_user,
                "assessment": assessment,
                "control": control,
                "csrf_token": csrf_token,
                "is_edit": False,
                "job_templates": job_templates,
                "breadcrumbs": [
                    {"label": "Compass", "link": "/"},
                    {
                        "label": assessment.product_name,
                        "link": f"/assessments/{assessment.assessment_id}",
                    },
                    {
                        "label": control.nist_control_id,
                        "link": f"/assessments/{assessment.assessment_id}/controls/{control.control_id}",
                    },
                ],
            },
        )
    except HTTPException as e:
        if e.status_code == 404:
            raise HTTPException(status_code=404, detail="Control not found")
        raise


@router.post("/new")
async def create_evidence(
    assessment_id: str,
    control_id: str,
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    evidence_type: str = Form(...),
    aws_account_id: Optional[str] = Form(None),
    csrf_token: str = Form(...),
    job_template_id: Optional[str] = Form(None),
    files: list[UploadFile] = File(default=[]),
    current_user: User = Depends(require_authenticated_user),
) -> RedirectResponse:
    """Handle evidence creation form submission."""
    # Validate CSRF token
    session_token = request.session.get("csrf_token")
    if not csrf_manager.validate_csrf_token(session_token, csrf_token):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")

    try:
        # Validate input data
        create_data = EvidenceRequest(
            title=title,
            description=description,
            evidence_type=evidence_type,
            job_template_id=job_template_id,
            aws_account_id=aws_account_id,
        )

        # Create evidence
        evidence = evidence_service.create_evidence(
            control_id, current_user.user_id, create_data
        )

        # Upload files if provided
        if files:
            for file in files:
                if file.filename:
                    content = await file.read()
                    s3_key = s3_service.upload_file(
                        content,
                        file.filename,
                        assessment_id,
                        control_id,
                        evidence.evidence_id,
                    )
                    evidence.add_file_key(s3_key)

        # Clear CSRF token
        request.session.pop("csrf_token", None)

        # Redirect to evidence detail page
        return RedirectResponse(
            url=f"/assessments/{assessment_id}/controls/{control_id}/evidence/{evidence.evidence_id}",
            status_code=303,
        )

    except (ValueError, HTTPException) as e:
        # Validation error - redisplay form with error
        try:
            control, assessment = evidence_service.get_control_and_assessment_info(
                control_id, current_user.user_id
            )
            csrf_token = csrf_manager.generate_csrf_token()
            request.session["csrf_token"] = csrf_token

            # Get scan job templates for user
            job_templates = JobTemplateService.get_active_templates()

            return templates.TemplateResponse(
                request,
                "pages/evidence/form.html",
                {
                    "request": request,
                    "title": "Create evidence",
                    "user": current_user,
                    "assessment": assessment,
                    "control": control,
                    "csrf_token": csrf_token,
                    "is_edit": False,
                    "error": format_validation_error(e),
                    "title_value": title,
                    "description": description,
                    "evidence_type": evidence_type,
                    "job_template_id": job_template_id,
                    "aws_account_id": aws_account_id,
                    "job_templates": job_templates,
                    "breadcrumbs": [
                        {"label": "Compass", "link": "/"},
                        {
                            "label": assessment.product_name,
                            "link": f"/assessments/{assessment.assessment_id}",
                        },
                        {
                            "label": control.nist_control_id,
                            "link": f"/assessments/{assessment.assessment_id}/controls/{control.control_id}",
                        },
                    ],
                },
            )
        except Exception:
            raise HTTPException(status_code=404, detail="Control not found")


@router.get("/{evidence_id}", response_class=HTMLResponse)
async def evidence_detail_page(
    assessment_id: str,
    control_id: str,
    evidence_id: str,
    request: Request,
    current_user: User = Depends(require_authenticated_user),
) -> HTMLResponse:
    """Display evidence details."""
    try:
        control, assessment = evidence_service.get_control_and_assessment_info(
            control_id, current_user.user_id
        )
        evidence = evidence_service.get_evidence(evidence_id, current_user.user_id)

        # Verify evidence belongs to control and assessment
        if evidence.control_id != control_id:
            raise HTTPException(status_code=404, detail="Evidence not found in control")
        if assessment.assessment_id != assessment_id:
            raise HTTPException(
                status_code=404, detail="Control not found in assessment"
            )

        # Generate CSRF token for delete functionality
        csrf_token = csrf_manager.generate_csrf_token()
        request.session["csrf_token"] = csrf_token

        # Get scan job information for automated collection evidence
        job_template = None
        job_executions = []

        if evidence.is_automated_collection:
            # Get scan job template information
            if evidence.job_template_id:
                job_template = JobTemplateService.get_template(evidence.job_template_id)

            # Get scan execution history and sort in newest first (reverse chronological)
            job_executions = JobExecutionService.get_evidence_executions(
                evidence.evidence_id, current_user.user_id
            )
            job_executions.sort(key=lambda x: x.completed_at, reverse=True)

        return templates.TemplateResponse(
            request,
            "pages/evidence/detail.html",
            {
                "request": request,
                "title": "Evidence details",
                "user": current_user,
                "assessment": assessment,
                "control": control,
                "evidence": evidence,
                "csrf_token": csrf_token,
                "job_template": job_template,
                "job_executions": job_executions,
                "job_execution_latest": job_executions[0] if job_executions else None,
                "breadcrumbs": [
                    {"label": "Compass", "link": "/"},
                    {
                        "label": assessment.product_name,
                        "link": f"/assessments/{assessment.assessment_id}",
                    },
                    {
                        "label": control.nist_control_id,
                        "link": f"/assessments/{assessment.assessment_id}/controls/{control.control_id}",
                    },
                ],
            },
        )
    except HTTPException as e:
        if e.status_code == 404:
            raise HTTPException(status_code=404, detail="Evidence not found")
        raise


@router.get("/{evidence_id}/edit", response_class=HTMLResponse)
async def edit_evidence_page(
    assessment_id: str,
    control_id: str,
    evidence_id: str,
    request: Request,
    current_user: User = Depends(require_authenticated_user),
) -> HTMLResponse:
    """Display form to edit evidence."""
    try:
        control, assessment = evidence_service.get_control_and_assessment_info(
            control_id, current_user.user_id
        )
        evidence = evidence_service.get_evidence(evidence_id, current_user.user_id)

        # Verify evidence belongs to control and assessment
        if evidence.control_id != control_id:
            raise HTTPException(status_code=404, detail="Evidence not found in control")
        if assessment.assessment_id != assessment_id:
            raise HTTPException(
                status_code=404, detail="Control not found in assessment"
            )

        # Generate CSRF token for form
        csrf_token = csrf_manager.generate_csrf_token()
        request.session["csrf_token"] = csrf_token

        # Get scan job templates for user
        job_templates = JobTemplateService.get_active_templates()

        return templates.TemplateResponse(
            request,
            "pages/evidence/form.html",
            {
                "request": request,
                "title": "Edit evidence",
                "user": current_user,
                "assessment": assessment,
                "control": control,
                "csrf_token": csrf_token,
                "is_edit": True,
                "evidence": evidence,
                "job_templates": job_templates,
                "breadcrumbs": [
                    {"label": "Compass", "link": "/"},
                    {
                        "label": assessment.product_name,
                        "link": f"/assessments/{assessment.assessment_id}",
                    },
                    {
                        "label": control.nist_control_id,
                        "link": f"/assessments/{assessment.assessment_id}/controls/{control.control_id}",
                    },
                    {
                        "label": evidence.title,
                        "link": f"/assessments/{assessment.assessment_id}/controls/{control.control_id}/evidence/{evidence.evidence_id}",
                    },
                ],
            },
        )
    except HTTPException as e:
        if e.status_code == 404:
            raise HTTPException(status_code=404, detail="Evidence not found")
        raise


@router.post("/{evidence_id}/edit")
async def update_evidence(
    assessment_id: str,
    control_id: str,
    evidence_id: str,
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    evidence_type: str = Form(...),
    aws_account_id: Optional[str] = Form(None),
    csrf_token: str = Form(...),
    job_template_id: Optional[str] = Form(None),
    files: list[UploadFile] = File(default=[]),
    files_to_delete: list[str] = Form(default=[]),
    current_user: User = Depends(require_authenticated_user),
) -> RedirectResponse:
    """Handle evidence update form submission."""
    # Validate CSRF token
    session_token = request.session.get("csrf_token")
    if not csrf_manager.validate_csrf_token(session_token, csrf_token):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")

    try:
        # Validate input data
        update_data = EvidenceRequest(
            title=title,
            description=description,
            evidence_type=evidence_type,
            aws_account_id=aws_account_id,
            job_template_id=job_template_id,
        )

        # Update evidence
        evidence = evidence_service.update_evidence(
            evidence_id, current_user.user_id, update_data
        )

        # Delete files marked for deletion
        if files_to_delete:
            for file_key in files_to_delete:
                if file_key in evidence.file_keys:
                    try:
                        s3_service.delete_file(file_key)
                        evidence.remove_file_key(file_key)
                    except Exception as e:
                        logger.error(f"Failed to delete file {file_key}: {str(e)}")

        # Upload files if provided
        if files:
            for file in files:
                if file.filename:
                    content = await file.read()
                    s3_key = s3_service.upload_file(
                        content,
                        file.filename,
                        assessment_id,
                        control_id,
                        evidence.evidence_id,
                    )
                    evidence.add_file_key(s3_key)

        # Clear CSRF token
        request.session.pop("csrf_token", None)

        # Redirect to evidence detail page
        return RedirectResponse(
            url=f"/assessments/{assessment_id}/controls/{control_id}/evidence/{evidence.evidence_id}",
            status_code=303,
        )

    except (ValueError, HTTPException) as e:
        # Error - redisplay form with error
        try:
            control, assessment = evidence_service.get_control_and_assessment_info(
                control_id, current_user.user_id
            )
            evidence = evidence_service.get_evidence(evidence_id, current_user.user_id)
            csrf_token = csrf_manager.generate_csrf_token()
            request.session["csrf_token"] = csrf_token

            # Get scan job templates for user
            job_templates = JobTemplateService.get_active_templates()

            return templates.TemplateResponse(
                request,
                "pages/evidence/form.html",
                {
                    "request": request,
                    "title": "Edit evidence",
                    "user": current_user,
                    "assessment": assessment,
                    "control": control,
                    "csrf_token": csrf_token,
                    "is_edit": True,
                    "evidence": evidence,
                    "error": format_validation_error(e),
                    "job_templates": job_templates,
                    "breadcrumbs": [
                        {"label": "Compass", "link": "/"},
                        {
                            "label": assessment.product_name,
                            "link": f"/assessments/{assessment.assessment_id}",
                        },
                        {
                            "label": control.nist_control_id,
                            "link": f"/assessments/{assessment.assessment_id}/controls/{control.control_id}",
                        },
                        {
                            "label": evidence.title,
                            "link": f"/assessments/{assessment.assessment_id}/controls/{control.control_id}/evidence/{evidence.evidence_id}",
                        },
                    ],
                },
            )
        except Exception:
            raise HTTPException(status_code=404, detail="Evidence not found")


@router.post("/{evidence_id}/delete")
async def delete_evidence(
    assessment_id: str,
    control_id: str,
    evidence_id: str,
    request: Request,
    csrf_token: str = Form(...),
    current_user: User = Depends(require_authenticated_user),
) -> RedirectResponse:
    """Handle evidence deletion."""
    # Validate CSRF token
    session_token = request.session.get("csrf_token")
    if not csrf_manager.validate_csrf_token(session_token, csrf_token):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")

    try:
        evidence_service.delete_evidence(evidence_id, current_user.user_id)

        # Clear CSRF token
        request.session.pop("csrf_token", None)

        return RedirectResponse(
            url=f"/assessments/{assessment_id}/controls/{control_id}",
            status_code=303,
        )

    except HTTPException as e:
        if e.status_code == 404:
            raise HTTPException(status_code=404, detail="Evidence not found")
        raise


@router.get("/{evidence_id}/files/metadata")
async def get_evidence_files_metadata(
    assessment_id: str,
    control_id: str,
    evidence_id: str,
    request: Request,
    current_user: User = Depends(require_authenticated_user),
) -> list[dict]:
    """Get metadata for all files associated with evidence."""
    try:
        # Verify user has access to this evidence
        evidence = evidence_service.get_entity_or_404(evidence_id, current_user.user_id)

        # Verify evidence belongs to the correct control and assessment
        control, assessment = evidence_service.get_control_and_assessment_info(
            control_id, current_user.user_id
        )

        if evidence.control_id != control_id:
            raise HTTPException(
                status_code=403, detail="Evidence does not belong to this control"
            )
        if assessment.assessment_id != assessment_id:
            raise HTTPException(
                status_code=403, detail="Control does not belong to this assessment"
            )

        # Get metadata for all files
        files_metadata = []
        for file_key in evidence.get_file_keys():
            try:
                metadata = s3_service.get_file_metadata(file_key)
                files_metadata.append(metadata)
            except HTTPException:
                # Skip files that no longer exist in S3
                continue

        return files_metadata

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get evidence files metadata: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get files metadata: {str(e)}"
        )


@router.get("/{evidence_id}/files/{file_key:path}")
async def download_evidence_file(
    assessment_id: str,
    control_id: str,
    evidence_id: str,
    file_key: str,
    request: Request,
    current_user: User = Depends(require_authenticated_user),
) -> Response:
    """Download evidence file with authorization check."""
    try:
        # Verify user has access to this evidence
        evidence = evidence_service.get_entity_or_404(evidence_id, current_user.user_id)

        # Verify evidence belongs to the correct control and assessment
        control, assessment = evidence_service.get_control_and_assessment_info(
            control_id, current_user.user_id
        )

        if evidence.control_id != control_id:
            raise HTTPException(
                status_code=403, detail="Evidence does not belong to this control"
            )
        if assessment.assessment_id != assessment_id:
            raise HTTPException(
                status_code=403, detail="Control does not belong to this assessment"
            )

        # Verify the file_key belongs to this evidence
        if file_key not in evidence.get_file_keys():
            raise HTTPException(status_code=404, detail="File not found in evidence")

        # Get file from S3
        content, content_type = s3_service.get_file_content(file_key)

        # Extract filename from S3 key
        filename = file_key.split("/")[-1]

        # Return file as response
        return Response(
            content=content,
            media_type=content_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download evidence file: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to download file: {str(e)}"
        )
