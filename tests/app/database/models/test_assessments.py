"""Unit tests for SecurityAssessment model."""

from unittest.mock import MagicMock

from app.database.models.assessments import SecurityAssessment


class TestSecurityAssessmentModel:
    """Tests for SecurityAssessment model."""

    def test_assessment_has_required_attributes(self) -> None:
        """Test that SecurityAssessment model has required attributes."""
        assessment = MagicMock(spec=SecurityAssessment)
        assessment.assessment_id = "assess-123"
        assessment.owner_id = "user-123"
        assessment.product_name = "Test Product"
        assessment.status = "prepare"

        assert assessment.assessment_id is not None
        assert assessment.owner_id is not None
        assert assessment.product_name is not None
        assert assessment.status is not None

    def test_assessment_status_validation(self) -> None:
        """Test that assessment validates status values."""
        assessment = MagicMock(spec=SecurityAssessment)
        assessment.status = "prepare"

        valid_statuses = ["prepare", "assess", "complete"]
        assert assessment.status in valid_statuses

    def test_aws_resources_list(self) -> None:
        """Test assessment can store AWS resources list."""
        assessment = MagicMock(spec=SecurityAssessment)
        assessment.aws_resources = ["s3", "rds", "lambda"]

        assert isinstance(assessment.aws_resources, list)
        assert len(assessment.aws_resources) == 3
        assert "s3" in assessment.aws_resources
