"""Control routes for web interface and API endpoints."""

from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from app.auth.middleware import require_authenticated_user
from app.database.models.users import User
from app.evidence.services import EvidenceService
from app.templates.utils import LocalizedTemplates
from app.controls.services import ControlService
from app.controls.validation import ControlCreateRequest, ControlUpdateRequest
from app.assessments.base import CSRFTokenManager
from app.assessments.services import AssessmentService

router = APIRouter(prefix="/assessments/{assessment_id}/controls", tags=["controls"])
templates = LocalizedTemplates(directory="./app/templates")
control_service = ControlService()
assessment_service = AssessmentService()
evidence_service = EvidenceService()
csrf_manager = CSRFTokenManager()


@router.get("/new", response_class=HTMLResponse)
async def create_control_page(
    assessment_id: str,
    request: Request,
    current_user: User = Depends(require_authenticated_user),
) -> HTMLResponse:
    """Display form to create new control."""
    try:
        # Get assessment info for context
        assessment = assessment_service.get_assessment(
            assessment_id, current_user.user_id
        )

        # Generate CSRF token for form
        csrf_token = csrf_manager.generate_csrf_token()
        request.session["csrf_token"] = csrf_token

        return templates.TemplateResponse(
            request,
            "pages/controls/form.html",
            {
                "request": request,
                "title": "create_control_title",
                "user": current_user,
                "assessment": assessment,
                "csrf_token": csrf_token,
                "is_edit": False,
                "breadcrumbs": [
                    {"label": "Compass", "link": "/"},
                    {
                        "label": assessment.product_name,
                        "link": f"/assessments/{assessment.assessment_id}",
                    },
                ],
            },
        )
    except HTTPException as e:
        if e.status_code == 404:
            raise HTTPException(status_code=404, detail="Assessment not found")
        raise


@router.post("/new")
async def create_control(
    assessment_id: str,
    request: Request,
    nist_control_id: str = Form(...),
    control_title: str = Form(...),
    control_description: str = Form(...),
    csrf_token: str = Form(...),
    current_user: User = Depends(require_authenticated_user),
) -> RedirectResponse:
    """Handle control creation form submission."""
    # Validate CSRF token
    session_token = request.session.get("csrf_token")
    if not csrf_manager.validate_csrf_token(session_token, csrf_token):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")

    try:
        # Validate input data
        create_data = ControlCreateRequest(
            nist_control_id=nist_control_id,
            control_title=control_title,
            control_description=control_description,
        )

        # Create control
        control = control_service.create_control(
            assessment_id, current_user.user_id, create_data
        )

        # Clear CSRF token
        request.session.pop("csrf_token", None)

        # Redirect to control detail page
        return RedirectResponse(
            url=f"/assessments/{assessment_id}/controls/{control.control_id}",
            status_code=303,
        )

    except (ValueError, HTTPException) as e:
        # Validation error - redisplay form with error
        try:
            assessment = assessment_service.get_assessment(
                assessment_id, current_user.user_id
            )
            csrf_token = csrf_manager.generate_csrf_token()
            request.session["csrf_token"] = csrf_token

            return templates.TemplateResponse(
                request,
                "pages/controls/form.html",
                {
                    "request": request,
                    "title": "create_control_title",
                    "user": current_user,
                    "assessment": assessment,
                    "csrf_token": csrf_token,
                    "is_edit": False,
                    "error": str(e),
                    "nist_control_id": nist_control_id,
                    "control_title": control_title,
                    "control_description": control_description,
                    "breadcrumbs": [
                        {"label": "Compass", "link": "/"},
                        {
                            "label": assessment.product_name,
                            "link": f"/assessments/{assessment.assessment_id}",
                        },
                    ],
                },
            )
        except Exception:
            raise HTTPException(status_code=404, detail="Assessment not found")


@router.get("/{control_id}", response_class=HTMLResponse)
async def control_detail_page(
    assessment_id: str,
    control_id: str,
    request: Request,
    current_user: User = Depends(require_authenticated_user),
) -> HTMLResponse:
    """Display control details."""
    try:
        assessment = assessment_service.get_assessment(
            assessment_id, current_user.user_id
        )
        control = control_service.get_control(control_id, current_user.user_id)
        evidences = evidence_service.list_evidence_by_control(
            control_id, current_user.user_id
        )

        # Verify control belongs to assessment
        if control.assessment_id != assessment_id:
            raise HTTPException(
                status_code=404, detail="Control not found in assessment"
            )

        return templates.TemplateResponse(
            request,
            "pages/controls/detail.html",
            {
                "request": request,
                "title": "control_detail_title",
                "user": current_user,
                "assessment": assessment,
                "control": control,
                "evidences": evidences,
                "breadcrumbs": [
                    {"label": "Compass", "link": "/"},
                    {
                        "label": assessment.product_name,
                        "link": f"/assessments/{assessment.assessment_id}",
                    },
                ],
            },
        )
    except HTTPException as e:
        if e.status_code == 404:
            raise HTTPException(status_code=404, detail="Control not found")
        raise


@router.get("/{control_id}/edit", response_class=HTMLResponse)
async def edit_control_page(
    assessment_id: str,
    control_id: str,
    request: Request,
    current_user: User = Depends(require_authenticated_user),
) -> HTMLResponse:
    """Display form to edit control."""
    try:
        assessment = assessment_service.get_assessment(
            assessment_id, current_user.user_id
        )
        control = control_service.get_control(control_id, current_user.user_id)

        # Verify control belongs to assessment
        if control.assessment_id != assessment_id:
            raise HTTPException(
                status_code=404, detail="Control not found in assessment"
            )

        # Generate CSRF token for form
        csrf_token = csrf_manager.generate_csrf_token()
        request.session["csrf_token"] = csrf_token

        return templates.TemplateResponse(
            request,
            "pages/controls/form.html",
            {
                "request": request,
                "title": "edit_control_title",
                "user": current_user,
                "assessment": assessment,
                "csrf_token": csrf_token,
                "is_edit": True,
                "control": control,
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


@router.post("/{control_id}/edit")
async def update_control(
    assessment_id: str,
    control_id: str,
    request: Request,
    nist_control_id: str = Form(...),
    control_title: str = Form(...),
    control_description: str = Form(...),
    implementation_status: str = Form(...),
    csrf_token: str = Form(...),
    current_user: User = Depends(require_authenticated_user),
) -> RedirectResponse:
    """Handle control update form submission."""
    # Validate CSRF token
    session_token = request.session.get("csrf_token")
    if not csrf_manager.validate_csrf_token(session_token, csrf_token):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")

    try:
        # Validate input data
        update_data = ControlUpdateRequest(
            nist_control_id=nist_control_id,
            control_title=control_title,
            control_description=control_description,
            implementation_status=implementation_status,
        )

        # Update control
        control = control_service.update_control(
            control_id, current_user.user_id, update_data
        )

        # Clear CSRF token
        request.session.pop("csrf_token", None)

        # Redirect to control detail page
        return RedirectResponse(
            url=f"/assessments/{assessment_id}/controls/{control.control_id}",
            status_code=303,
        )

    except (ValueError, HTTPException) as e:
        # Error - redisplay form with error
        try:
            assessment = assessment_service.get_assessment(
                assessment_id, current_user.user_id
            )
            control = control_service.get_control(control_id, current_user.user_id)
            csrf_token = csrf_manager.generate_csrf_token()
            request.session["csrf_token"] = csrf_token

            return templates.TemplateResponse(
                request,
                "pages/controls/form.html",
                {
                    "request": request,
                    "title": "edit_control_title",
                    "user": current_user,
                    "assessment": assessment,
                    "csrf_token": csrf_token,
                    "is_edit": True,
                    "control": control,
                    "error": str(e),
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


@router.post("/{control_id}/delete")
async def delete_control(
    assessment_id: str,
    control_id: str,
    request: Request,
    csrf_token: str = Form(...),
    current_user: User = Depends(require_authenticated_user),
) -> RedirectResponse:
    """Handle control deletion."""
    # Validate CSRF token
    session_token = request.session.get("csrf_token")
    if not csrf_manager.validate_csrf_token(session_token, csrf_token):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")

    try:
        control_service.delete_control(control_id, current_user.user_id)

        # Clear CSRF token
        request.session.pop("csrf_token", None)

        return RedirectResponse(
            url=f"/assessments/{assessment_id}/controls/", status_code=303
        )

    except HTTPException as e:
        if e.status_code == 404:
            raise HTTPException(status_code=404, detail="Control not found")
        raise
