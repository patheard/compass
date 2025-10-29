"""Unit tests for evidence validation."""

import pytest

from app.evidence.validation import EvidenceRequest


class TestEvidenceRequest:
    """Tests for EvidenceRequest validation."""

    def test_valid_request_with_all_fields(self) -> None:
        """Test validation with all fields provided."""
        data = EvidenceRequest(
            title="Test Evidence",
            description="Test description",
            evidence_type="document",
            status="compliant",
            aws_account_id="123456789012",
            job_template_id="test-template-id",
        )

        assert data.title == "Test Evidence"
        assert data.description == "Test description"
        assert data.evidence_type == "document"
        assert data.status == "compliant"
        assert data.aws_account_id == "123456789012"
        assert data.job_template_id == "test-template-id"

    def test_valid_request_with_minimal_fields(self) -> None:
        """Test validation with only required fields."""
        data = EvidenceRequest(
            title="Test Evidence",
            description="Test description",
            evidence_type="document",
        )

        assert data.title == "Test Evidence"
        assert data.description == "Test description"
        assert data.evidence_type == "document"
        assert data.status is None
        assert data.aws_account_id is None
        assert data.job_template_id is None

    def test_validate_title_empty_string(self) -> None:
        """Test that empty title is rejected."""
        with pytest.raises(ValueError):
            EvidenceRequest(
                title="   ",
                description="Test description",
                evidence_type="document",
            )

    def test_validate_description_empty_string(self) -> None:
        """Test that empty description is rejected."""
        with pytest.raises(ValueError):
            EvidenceRequest(
                title="Test Evidence",
                description="   ",
                evidence_type="document",
            )

    def test_validate_evidence_type_invalid(self) -> None:
        """Test that invalid evidence type is rejected."""
        with pytest.raises(ValueError, match="Evidence type must be one of"):
            EvidenceRequest(
                title="Test Evidence",
                description="Test description",
                evidence_type="invalid_type",
            )

    def test_validate_status_invalid(self) -> None:
        """Test that invalid status is rejected."""
        with pytest.raises(ValueError, match="Status must be one of"):
            EvidenceRequest(
                title="Test Evidence",
                description="Test description",
                evidence_type="document",
                status="invalid_status",
            )

    def test_validate_status_empty_string(self) -> None:
        """Test that empty status string is converted to None."""
        data = EvidenceRequest(
            title="Test Evidence",
            description="Test description",
            evidence_type="document",
            status="",
        )

        assert data.status is None

    def test_validate_aws_account_id_invalid_length(self) -> None:
        """Test that AWS account ID with incorrect length is rejected."""
        with pytest.raises(
            ValueError, match="aws_account_id must be a 12-digit numeric AWS account id"
        ):
            EvidenceRequest(
                title="Test Evidence",
                description="Test description",
                evidence_type="document",
                aws_account_id="12345",
            )

    def test_validate_aws_account_id_non_numeric(self) -> None:
        """Test that non-numeric AWS account ID is rejected."""
        with pytest.raises(
            ValueError, match="aws_account_id must be a 12-digit numeric AWS account id"
        ):
            EvidenceRequest(
                title="Test Evidence",
                description="Test description",
                evidence_type="document",
                aws_account_id="12345678901a",
            )

    def test_validate_aws_account_id_none_string(self) -> None:
        """Test that 'None' string is converted to None."""
        data = EvidenceRequest(
            title="Test Evidence",
            description="Test description",
            evidence_type="document",
            aws_account_id="None",
        )

        assert data.aws_account_id is None

    def test_validate_aws_account_id_empty_string(self) -> None:
        """Test that empty string is converted to None."""
        data = EvidenceRequest(
            title="Test Evidence",
            description="Test description",
            evidence_type="document",
            aws_account_id="   ",
        )

        assert data.aws_account_id is None

    def test_validate_job_template_id_none(self) -> None:
        """Test that None job template ID is accepted."""
        data = EvidenceRequest(
            title="Test Evidence",
            description="Test description",
            evidence_type="document",
            job_template_id=None,
        )

        assert data.job_template_id is None
