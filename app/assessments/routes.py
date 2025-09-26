"""Assessment routes for web interface and API endpoints."""

from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from app.auth.middleware import require_authenticated_user
from app.database.models.users import User
from app.templates.utils import LocalizedTemplates
from app.assessments.services import AssessmentService, GitHubService
from app.assessments.validation import AssessmentRequest
from app.assessments.base import CSRFTokenManager, format_validation_error
from app.controls.services import ControlService

router = APIRouter(prefix="/assessments", tags=["assessments"])
templates = LocalizedTemplates(directory="./app/templates")
assessment_service = AssessmentService()
control_service = ControlService()
csrf_manager = CSRFTokenManager()


@router.get("/new", response_class=HTMLResponse)
async def create_assessment_page(
    request: Request, current_user: User = Depends(require_authenticated_user)
) -> HTMLResponse:
    """Display form to create new assessment."""
    # Generate CSRF token for form
    csrf_token = csrf_manager.generate_csrf_token()
    request.session["csrf_token"] = csrf_token

    return templates.TemplateResponse(
        request,
        "pages/assessments/form.html",
        {
            "request": request,
            "title": "Create assessment",
            "user": current_user,
            "csrf_token": csrf_token,
            "is_edit": False,
            "breadcrumbs": [
                {"label": "Compass", "link": "/"},
            ],
        },
    )


@router.post("/new")
async def create_assessment(
    request: Request,
    product_name: str = Form(...),
    product_description: str = Form(...),
    aws_account_id: str = Form(""),
    github_repo_controls: str = Form(""),
    csrf_token: str = Form(...),
    current_user: User = Depends(require_authenticated_user),
) -> RedirectResponse:
    """Handle assessment creation form submission."""
    # Validate CSRF token
    session_token = request.session.get("csrf_token")
    if not csrf_manager.validate_csrf_token(session_token, csrf_token):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")

    try:
        # Validate input data
        create_data = AssessmentRequest(
            product_name=product_name,
            product_description=product_description,
            aws_account_id=aws_account_id if aws_account_id.strip() else None,
            github_repo_controls=github_repo_controls
            if github_repo_controls.strip()
            else None,
        )

        # Create assessment
        assessment = assessment_service.create_assessment(
            current_user.user_id, create_data
        )

        # Clear CSRF token
        request.session.pop("csrf_token", None)

        # Redirect to assessment detail page
        return RedirectResponse(
            url=f"/assessments/{assessment.assessment_id}", status_code=303
        )

    except ValueError as e:
        # Validation error - redisplay form with error
        csrf_token = csrf_manager.generate_csrf_token()
        request.session["csrf_token"] = csrf_token

        return templates.TemplateResponse(
            request,
            "pages/assessments/form.html",
            {
                "request": request,
                "title": "Create assessment",
                "user": current_user,
                "csrf_token": csrf_token,
                "is_edit": False,
                "error": format_validation_error(e),
                "product_name": product_name,
                "product_description": product_description,
                "aws_account_id": aws_account_id,
                "github_repo_controls": github_repo_controls,
                "breadcrumbs": [
                    {"label": "Compass", "link": "/"},
                ],
            },
        )


@router.get("/{assessment_id}", response_class=HTMLResponse)
async def assessment_detail_page(
    assessment_id: str,
    request: Request,
    current_user: User = Depends(require_authenticated_user),
) -> HTMLResponse:
    """Display assessment details."""
    try:
        assessment = assessment_service.get_assessment(
            assessment_id, current_user.user_id
        )
        controls = control_service.list_controls_by_assessment(
            assessment_id, current_user.user_id
        )

        # Generate CSRF token for delete functionality
        csrf_token = csrf_manager.generate_csrf_token()
        request.session["csrf_token"] = csrf_token

        return templates.TemplateResponse(
            request,
            "pages/assessments/detail.html",
            {
                "request": request,
                "title": "Assessment details",
                "user": current_user,
                "assessment": assessment,
                "controls": controls,
                "csrf_token": csrf_token,
                "breadcrumbs": [
                    {"label": "Compass", "link": "/"},
                ],
            },
        )
    except HTTPException as e:
        if e.status_code == 404:
            raise HTTPException(status_code=404, detail="Assessment not found")
        raise


@router.get("/{assessment_id}/edit", response_class=HTMLResponse)
async def edit_assessment_page(
    assessment_id: str,
    request: Request,
    current_user: User = Depends(require_authenticated_user),
) -> HTMLResponse:
    """Display form to edit assessment."""
    try:
        assessment = assessment_service.get_assessment(
            assessment_id, current_user.user_id
        )

        # Generate CSRF token for form
        csrf_token = csrf_manager.generate_csrf_token()
        request.session["csrf_token"] = csrf_token

        return templates.TemplateResponse(
            request,
            "pages/assessments/form.html",
            {
                "request": request,
                "title": "Edit assessment",
                "user": current_user,
                "csrf_token": csrf_token,
                "is_edit": True,
                "assessment": assessment,
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


@router.post("/{assessment_id}/edit")
async def update_assessment(
    assessment_id: str,
    request: Request,
    product_name: str = Form(...),
    product_description: str = Form(...),
    status: str = Form(...),
    aws_account_id: str = Form(""),
    github_repo_controls: str = Form(""),
    csrf_token: str = Form(...),
    current_user: User = Depends(require_authenticated_user),
) -> RedirectResponse:
    """Handle assessment update form submission."""
    # Validate CSRF token
    session_token = request.session.get("csrf_token")
    if not csrf_manager.validate_csrf_token(session_token, csrf_token):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")

    try:
        # Validate input data
        update_data = AssessmentRequest(
            product_name=product_name,
            product_description=product_description,
            status=status,
            aws_account_id=aws_account_id if aws_account_id.strip() else None,
            github_repo_controls=github_repo_controls
            if github_repo_controls.strip()
            else None,
        )

        # Update assessment
        assessment = assessment_service.update_assessment(
            assessment_id, current_user.user_id, update_data
        )

        # Clear CSRF token
        request.session.pop("csrf_token", None)

        # Redirect to assessment detail page
        return RedirectResponse(
            url=f"/assessments/{assessment.assessment_id}", status_code=303
        )

    except (ValueError, HTTPException) as e:
        # Error - redisplay form with error
        try:
            assessment = assessment_service.get_assessment(
                assessment_id, current_user.user_id
            )
            csrf_token = csrf_manager.generate_csrf_token()
            request.session["csrf_token"] = csrf_token

            return templates.TemplateResponse(
                request,
                "pages/assessments/form.html",
                {
                    "request": request,
                    "title": "Edit assessment",
                    "user": current_user,
                    "csrf_token": csrf_token,
                    "is_edit": True,
                    "assessment": assessment,
                    "error": format_validation_error(e),
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


@router.post("/{assessment_id}/delete")
async def delete_assessment(
    assessment_id: str,
    request: Request,
    csrf_token: str = Form(...),
    current_user: User = Depends(require_authenticated_user),
) -> RedirectResponse:
    """Handle assessment deletion."""
    # Validate CSRF token
    session_token = request.session.get("csrf_token")
    if not csrf_manager.validate_csrf_token(session_token, csrf_token):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")

    try:
        assessment_service.delete_assessment(assessment_id, current_user.user_id)

        # Clear CSRF token
        request.session.pop("csrf_token", None)

        return RedirectResponse(url="/", status_code=303)

    except HTTPException as e:
        if e.status_code == 404:
            raise HTTPException(status_code=404, detail="Assessment not found")
        raise


@router.get("/{assessment_id}/import", response_class=HTMLResponse)
async def import_assessment_page(
    assessment_id: str,
    request: Request,
    current_user: User = Depends(require_authenticated_user),
) -> HTMLResponse:
    """Display form to begin the GitHub repo controls import."""
    try:
        assessment = assessment_service.get_assessment(
            assessment_id, current_user.user_id
        )

        # Generate CSRF token for form
        csrf_token = csrf_manager.generate_csrf_token()
        request.session["csrf_token"] = csrf_token

        return templates.TemplateResponse(
            request,
            "pages/assessments/import_setup.html",
            {
                "request": request,
                "title": "Import controls",
                "user": current_user,
                "csrf_token": csrf_token,
                "assessment": assessment,
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


@router.post("/{assessment_id}/import", response_class=HTMLResponse)
async def import_controls_from_github(
    assessment_id: str,
    request: Request,
    github_repo_controls: str = Form(...),
    github_pat: str = Form(...),
    csrf_token: str = Form(...),
    current_user: User = Depends(require_authenticated_user),
) -> HTMLResponse:
    """Handle GitHub repository controls import."""
    # Validate CSRF token
    session_token = request.session.get("csrf_token")
    if not csrf_manager.validate_csrf_token(session_token, csrf_token):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")

    try:
        # Get assessment
        assessment = assessment_service.get_assessment(
            assessment_id, current_user.user_id
        )

        # Initialize GitHub service with PAT
        github_service = GitHubService(github_pat)

        # Import issues as control data
        controls_data = github_service.import_issues_as_controls(github_repo_controls)

        if not controls_data:
            raise HTTPException(
                status_code=400, detail="No valid issues found in the repository"
            )

        # Create controls from GitHub issues
        result = control_service.create_controls_from_github(
            assessment_id, current_user.user_id, controls_data
        )

        # Clear CSRF token
        request.session.pop("csrf_token", None)

        return templates.TemplateResponse(
            request,
            "pages/assessments/import_results.html",
            {
                "request": request,
                "title": "Import results",
                "user": current_user,
                "assessment": assessment,
                "csrf_token": csrf_token,
                "result": result,
                "breadcrumbs": [
                    {"label": "Compass", "link": "/"},
                    {
                        "label": assessment.product_name,
                        "link": f"/assessments/{assessment.assessment_id}",
                    },
                ],
            },
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Handle other errors and redisplay form
        try:
            assessment = assessment_service.get_assessment(
                assessment_id, current_user.user_id
            )
            csrf_token = csrf_manager.generate_csrf_token()
            request.session["csrf_token"] = csrf_token

            return templates.TemplateResponse(
                request,
                "pages/assessments/import_setup.html",
                {
                    "request": request,
                    "title": "Import controls",
                    "user": current_user,
                    "csrf_token": csrf_token,
                    "assessment": assessment,
                    "error": format_validation_error(e),
                    "github_repo_controls": github_repo_controls,
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
