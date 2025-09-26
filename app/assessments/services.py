"""Assessment service layer for business logic and data operations."""

import re
from typing import List, Dict, Any
from fastapi import HTTPException
from github import Github
from github.Repository import Repository
from github.Issue import Issue
from app.database.models.assessments import SecurityAssessment
from app.database.models.controls import Control
from app.database.models.evidence import Evidence
from app.assessments.base import BaseService
from app.assessments.validation import (
    AssessmentCreateRequest,
    AssessmentUpdateRequest,
    AssessmentResponse,
)


class AssessmentService(BaseService[SecurityAssessment]):
    """Service class for assessment CRUD operations."""

    def __init__(self):
        super().__init__(SecurityAssessment)

    def validate_ownership(self, entity: SecurityAssessment, user_id: str) -> bool:
        """Validate that the user owns the assessment."""
        return entity.is_owner(user_id)

    def get_user_entities(self, user_id: str) -> List[SecurityAssessment]:
        """Get all assessments belonging to a user."""
        try:
            return SecurityAssessment.get_by_owner(user_id)
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to retrieve assessments: {str(e)}"
            )

    def create_assessment(
        self, user_id: str, data: AssessmentCreateRequest
    ) -> AssessmentResponse:
        """Create a new assessment."""
        try:
            assessment = SecurityAssessment.create_assessment(
                creator_id=user_id,
                product_name=data.product_name,
                product_description=data.product_description,
                aws_account_id=data.aws_account_id,
                github_repo_controls=data.github_repo_controls,
            )
            return self._to_response(assessment)
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to create assessment: {str(e)}"
            )

    def get_assessment(self, assessment_id: str, user_id: str) -> AssessmentResponse:
        """Get a specific assessment by ID."""
        assessment = self.get_entity_or_404(assessment_id, user_id)
        return self._to_response(assessment)

    def list_assessments(self, user_id: str) -> List[AssessmentResponse]:
        """List all assessments for a user."""
        assessments = self.get_user_entities(user_id)
        return [self._to_response(assessment) for assessment in assessments]

    def update_assessment(
        self, assessment_id: str, user_id: str, data: AssessmentUpdateRequest
    ) -> AssessmentResponse:
        """Update an existing assessment."""
        assessment = self.get_entity_or_404(assessment_id, user_id)

        try:
            # Update only provided fields
            if data.product_name is not None:
                assessment.product_name = data.product_name

            if data.product_description is not None:
                assessment.product_description = data.product_description

            if data.aws_account_id is not None:
                assessment.aws_account_id = data.aws_account_id

            if data.github_repo_controls is not None:
                assessment.github_repo_controls = data.github_repo_controls

            if data.status is not None:
                assessment.update_status(data.status)
            else:
                assessment.save()

            return self._to_response(assessment)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to update assessment: {str(e)}"
            )

    def delete_assessment(self, assessment_id: str, user_id: str) -> None:
        """Delete an assessment and all associated controls and evidence."""
        assessment = self.get_entity_or_404(assessment_id, user_id)

        try:
            # Get all controls for this assessment
            controls = Control.get_by_assessment(assessment_id)

            # Delete all evidence for each control
            for control in controls:
                evidence_list = Evidence.get_by_control(control.control_id)
                for evidence in evidence_list:
                    evidence.delete()

            # Delete all controls
            for control in controls:
                control.delete()

            # Finally delete the assessment
            assessment.delete()
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to delete assessment: {str(e)}"
            )

    def _to_response(self, assessment: SecurityAssessment) -> AssessmentResponse:
        """Convert assessment model to response schema."""
        return AssessmentResponse(
            assessment_id=assessment.assessment_id,
            owner_id=assessment.owner_id,
            product_name=assessment.product_name,
            product_description=assessment.product_description,
            status=assessment.status,
            aws_account_id=assessment.aws_account_id,
            github_repo_controls=assessment.github_repo_controls,
            created_at=assessment.created_at,
            updated_at=assessment.updated_at,
        )


class GitHubService:
    """Service for interacting with GitHub API to import issues."""

    def __init__(self, access_token: str):
        """Initialize GitHub client with access token."""
        self.github = Github(access_token)

    def get_repository(self, repo_url: str) -> Repository:
        """Extract repository from URL and return GitHub repository object."""
        # Extract owner/repo from various GitHub URL formats
        patterns = [
            r"https://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$",
            r"git@github\.com:([^/]+)/([^/]+?)(?:\.git)?/?$",
            r"([^/]+)/([^/]+)$",  # Direct owner/repo format
        ]

        repo_path = None
        for pattern in patterns:
            match = re.match(pattern, repo_url.strip())
            if match:
                owner, repo_name = match.groups()
                repo_path = f"{owner}/{repo_name}"
                break

        if not repo_path:
            raise ValueError(f"Invalid GitHub repository URL format: {repo_url}")

        try:
            return self.github.get_repo(repo_path)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to access repository {repo_path}: {str(e)}",
            )

    def get_open_issues(self, repo: Repository) -> List[Issue]:
        """Get all open issues from a repository with pagination."""
        try:
            issues = []
            # Get open issues, paginated automatically by PyGithub
            for issue in repo.get_issues(state="open"):
                # Skip pull requests (they appear as issues in GitHub API)
                if not issue.pull_request:
                    issues.append(issue)
            return issues
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to retrieve issues: {str(e)}"
            )

    def parse_issue_to_control(self, issue: Issue) -> Dict[str, Any]:
        """Parse a GitHub issue into control data."""
        # Parse title: "NIST-ID: Control Title"
        title_parts = issue.title.split(":", 1)
        if len(title_parts) != 2:
            raise ValueError(f"Issue title format invalid: {issue.title}")

        nist_control_id = title_parts[0].strip()
        control_title = title_parts[1].strip()

        # Parse body for control description sections
        control_description = self._parse_control_description(issue.body or "")

        return {
            "nist_control_id": nist_control_id,
            "control_title": control_title,
            "control_description": control_description,
            "github_issue_number": issue.number,
            "github_issue_url": issue.html_url,
        }

    def _parse_control_description(self, body: str) -> str:
        """Extract content from issue body up to Control Management section."""
        if not body:
            return ""

        # Find the Control Management section and cut everything after it
        control_management_index = body.find("# Control Management")
        if control_management_index != -1:
            body = body[:control_management_index]

        # Remove the Control Definition header if present
        body = body.replace("# Control Definition", "")

        return body.strip()

    def import_issues_as_controls(self, repo_url: str) -> List[Dict[str, Any]]:
        """Import all open issues from a repository as control data."""
        repo = self.get_repository(repo_url)
        issues = self.get_open_issues(repo)

        controls_data = []
        errors = []

        for issue in issues:
            try:
                control_data = self.parse_issue_to_control(issue)
                controls_data.append(control_data)
            except ValueError as e:
                errors.append(f"Issue #{issue.number}: {str(e)}")

        if errors:
            # Log errors but don't fail completely if some issues are parseable
            print(f"Errors parsing some issues: {errors}")

        return controls_data
