"""Unit tests for assessment validation."""

import pytest

from app.assessments.validation import AssessmentRequest


class TestAssessmentRequest:
    """Tests for AssessmentRequest validation."""

    def test_valid_request_with_all_fields(self) -> None:
        """Test validation with all fields provided."""
        data = AssessmentRequest(
            product_name="Test Product",
            product_description="Test description",
            status="prepare",
            aws_account_id="123456789012",
            github_repo_controls="owner/repo",
            aws_resources=["s3"],
        )

        assert data.product_name == "Test Product"
        assert data.product_description == "Test description"
        assert data.status == "prepare"
        assert data.aws_account_id == "123456789012"
        assert data.github_repo_controls == "owner/repo"
        assert data.aws_resources == ["s3"]

    def test_valid_request_with_minimal_fields(self) -> None:
        """Test validation with only required fields."""
        data = AssessmentRequest(
            product_name="Test Product",
            product_description="Test description",
        )

        assert data.product_name == "Test Product"
        assert data.product_description == "Test description"
        assert data.status is None
        assert data.aws_account_id is None
        assert data.github_repo_controls is None
        assert data.aws_resources is None

    def test_validate_product_name_empty_string(self) -> None:
        """Test that empty product name is rejected."""
        with pytest.raises(ValueError):
            AssessmentRequest(
                product_name="   ",
                product_description="Test description",
            )

    def test_validate_product_description_empty_string(self) -> None:
        """Test that empty product description is rejected."""
        with pytest.raises(ValueError):
            AssessmentRequest(
                product_name="Test Product",
                product_description="   ",
            )

    def test_validate_status_invalid(self) -> None:
        """Test that invalid status is rejected."""
        with pytest.raises(ValueError, match="Status must be one of"):
            AssessmentRequest(
                product_name="Test Product",
                product_description="Test description",
                status="invalid_status",
            )

    def test_validate_status_none(self) -> None:
        """Test that None status is accepted."""
        data = AssessmentRequest(
            product_name="Test Product",
            product_description="Test description",
            status=None,
        )

        assert data.status is None

    def test_validate_aws_account_id_invalid_length(self) -> None:
        """Test that AWS account ID with incorrect length is rejected."""
        with pytest.raises(ValueError, match="AWS account ID must be 12 digits"):
            AssessmentRequest(
                product_name="Test Product",
                product_description="Test description",
                aws_account_id="12345",
            )

    def test_validate_aws_account_id_non_numeric(self) -> None:
        """Test that non-numeric AWS account ID is rejected."""
        with pytest.raises(ValueError, match="AWS account ID must be 12 digits"):
            AssessmentRequest(
                product_name="Test Product",
                product_description="Test description",
                aws_account_id="12345678901a",
            )

    def test_validate_aws_account_id_none(self) -> None:
        """Test that None AWS account ID is accepted."""
        data = AssessmentRequest(
            product_name="Test Product",
            product_description="Test description",
            aws_account_id=None,
        )

        assert data.aws_account_id is None

    def test_validate_github_repo_controls_none(self) -> None:
        """Test that None GitHub repo is accepted."""
        data = AssessmentRequest(
            product_name="Test Product",
            product_description="Test description",
            github_repo_controls=None,
        )

        assert data.github_repo_controls is None

    def test_validate_aws_resources_invalid(self) -> None:
        """Test that invalid AWS resources are rejected."""
        with pytest.raises(ValueError, match="AWS resources contains invalid entries"):
            AssessmentRequest(
                product_name="Test Product",
                product_description="Test description",
                aws_resources=["Invalid::Resource"],
            )

    def test_validate_aws_resources_none(self) -> None:
        """Test that None AWS resources is accepted."""
        data = AssessmentRequest(
            product_name="Test Product",
            product_description="Test description",
            aws_resources=None,
        )

        assert data.aws_resources is None
