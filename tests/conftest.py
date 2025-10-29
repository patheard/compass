"""Pytest configuration and shared fixtures."""

from datetime import datetime, timezone
from typing import Generator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database.models.users import User
from app.database.models.assessments import SecurityAssessment
from app.database.models.controls import Control
from app.database.models.evidence import Evidence


@pytest.fixture
def sample_secret_key() -> str:
    """Provide a sample secret key for testing."""
    return "test-secret-key-12345"


@pytest.fixture
def sample_origins() -> list[str]:
    """Provide sample origins for CORS testing."""
    return [
        "http://localhost:8000",
        "http://localhost:3000",
        "https://example.com",
    ]


@pytest.fixture
def test_client() -> Generator[TestClient, None, None]:
    """Provide a FastAPI test client."""
    with TestClient(app) as client:
        yield client


@pytest.fixture
def mock_user() -> User:
    """Create a mock user for testing."""
    user = MagicMock(spec=User)
    user.user_id = "test-user-id-123"
    user.google_id = "google-123456"
    user.email = "test@example.com"
    user.name = "Test User"
    user.created_at = datetime.now(timezone.utc).isoformat()
    user.to_dict.return_value = {
        "user_id": user.user_id,
        "google_id": user.google_id,
        "email": user.email,
        "name": user.name,
        "created_at": user.created_at,
    }
    return user


@pytest.fixture
def mock_assessment() -> SecurityAssessment:
    """Create a mock security assessment for testing."""
    assessment = MagicMock(spec=SecurityAssessment)
    assessment.assessment_id = "test-assessment-id-123"
    assessment.owner_id = "test-user-id-123"
    assessment.product_name = "Test Product"
    assessment.product_description = "Test product description"
    assessment.status = "prepare"
    assessment.aws_account_id = "123456789012"
    assessment.github_repo_controls = "owner/repo"
    assessment.aws_resources = ["s3", "rds"]
    assessment.created_at = datetime.now(timezone.utc).isoformat()
    assessment.updated_at = datetime.now(timezone.utc).isoformat()
    assessment.is_owner.return_value = True
    return assessment


@pytest.fixture
def mock_control() -> Control:
    """Create a mock control for testing."""
    control = MagicMock(spec=Control)
    control.control_id = "test-control-id-123"
    control.assessment_id = "test-assessment-id-123"
    control.nist_control_id = "AC-1"
    control.control_title = "Access Control Policy"
    control.control_description = "Test control description"
    control.status = "not_started"
    control.github_issue_number = 1
    control.github_issue_url = "https://github.com/owner/repo/issues/1"
    control.created_at = datetime.now(timezone.utc).isoformat()
    control.updated_at = datetime.now(timezone.utc).isoformat()
    return control


@pytest.fixture
def mock_evidence() -> Evidence:
    """Create a mock evidence for testing."""
    evidence = MagicMock(spec=Evidence)
    evidence.evidence_id = "test-evidence-id-123"
    evidence.control_id = "test-control-id-123"
    evidence.title = "Test Evidence"
    evidence.description = "Test evidence description"
    evidence.evidence_type = "document"
    evidence.status = "compliant"
    evidence.file_keys = []
    evidence.aws_account_id = "123456789012"
    evidence.job_template_id = None
    evidence.created_at = datetime.now(timezone.utc).isoformat()
    evidence.updated_at = datetime.now(timezone.utc).isoformat()
    evidence.get_file_keys.return_value = []
    evidence.has_file.return_value = False
    evidence.is_automated_collection.return_value = False
    return evidence
