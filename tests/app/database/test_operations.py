"""Unit tests for database operations."""

from unittest.mock import MagicMock, patch

import pytest

from app.database.operations import DatabaseOperations


@pytest.fixture
def mock_user() -> MagicMock:
    """Create a mock user."""
    user = MagicMock()
    user.user_id = "test-user-id"
    user.google_id = "test-google-id"
    user.email = "test@example.com"
    user.name = "Test User"
    return user


@pytest.fixture
def mock_assessment() -> MagicMock:
    """Create a mock security assessment."""
    assessment = MagicMock()
    assessment.assessment_id = "test-assessment-id"
    assessment.owner_id = "test-user-id"
    assessment.product_name = "Test Product"
    assessment.status = "prepare"
    assessment.is_owner.return_value = True
    return assessment


@pytest.fixture
def mock_control() -> MagicMock:
    """Create a mock control."""
    control = MagicMock()
    control.control_id = "test-control-id"
    control.assessment_id = "test-assessment-id"
    control.nist_control_id = "AC-1"
    control.status = "not_started"
    return control


@pytest.fixture
def mock_evidence() -> MagicMock:
    """Create a mock evidence."""
    evidence = MagicMock()
    evidence.evidence_id = "test-evidence-id"
    evidence.control_id = "test-control-id"
    evidence.title = "Test Evidence"
    return evidence


class TestDatabaseOperations:
    """Tests for DatabaseOperations class."""

    @patch("app.database.operations.User")
    def test_get_user_by_google_id(
        self, mock_user_class: MagicMock, mock_user: MagicMock
    ) -> None:
        """Test getting user by Google ID."""
        mock_user_class.get_by_google_id.return_value = mock_user

        result = DatabaseOperations.get_user_by_google_id("test-google-id")

        assert result == mock_user
        mock_user_class.get_by_google_id.assert_called_once_with("test-google-id")

    @patch("app.database.operations.User")
    def test_get_user_by_email(
        self, mock_user_class: MagicMock, mock_user: MagicMock
    ) -> None:
        """Test getting user by email."""
        mock_user_class.get_by_email.return_value = mock_user

        result = DatabaseOperations.get_user_by_email("test@example.com")

        assert result == mock_user
        mock_user_class.get_by_email.assert_called_once_with("test@example.com")

    @patch("app.database.operations.SecurityAssessment")
    def test_get_user_assessments(
        self, mock_assessment_class: MagicMock, mock_assessment: MagicMock
    ) -> None:
        """Test getting user assessments."""
        mock_assessment_class.get_by_owner.return_value = [mock_assessment]

        result = DatabaseOperations.get_user_assessments("test-user-id")

        assert result == [mock_assessment]
        mock_assessment_class.get_by_owner.assert_called_once_with("test-user-id")

    @patch("app.database.operations.SecurityAssessment")
    def test_check_user_assessment_access_success(
        self, mock_assessment_class: MagicMock, mock_assessment: MagicMock
    ) -> None:
        """Test checking user assessment access successfully."""
        mock_assessment_class.get.return_value = mock_assessment
        mock_assessment.is_owner.return_value = True

        result = DatabaseOperations.check_user_assessment_access(
            "test-user-id", "test-assessment-id"
        )

        assert result is True

    @patch("app.database.operations.SecurityAssessment")
    def test_check_user_assessment_access_denied(
        self, mock_assessment_class: MagicMock, mock_assessment: MagicMock
    ) -> None:
        """Test checking user assessment access denied."""
        mock_assessment_class.get.return_value = mock_assessment
        mock_assessment.is_owner.return_value = False

        result = DatabaseOperations.check_user_assessment_access(
            "different-user-id", "test-assessment-id"
        )

        assert result is False

    @patch("app.database.operations.SecurityAssessment")
    def test_check_user_assessment_access_not_found(
        self, mock_assessment_class: MagicMock
    ) -> None:
        """Test checking user assessment access when not found."""
        mock_assessment_class.DoesNotExist = Exception
        mock_assessment_class.get.side_effect = Exception()

        result = DatabaseOperations.check_user_assessment_access(
            "test-user-id", "nonexistent-id"
        )

        assert result is False

    @patch("app.database.operations.Control")
    def test_get_assessment_controls(
        self, mock_control_class: MagicMock, mock_control: MagicMock
    ) -> None:
        """Test getting assessment controls."""
        mock_control_class.get_by_assessment.return_value = [mock_control]

        result = DatabaseOperations.get_assessment_controls("test-assessment-id")

        assert result == [mock_control]
        mock_control_class.get_by_assessment.assert_called_once_with(
            "test-assessment-id"
        )

    @patch("app.database.operations.Evidence")
    def test_get_control_evidence(
        self, mock_evidence_class: MagicMock, mock_evidence: MagicMock
    ) -> None:
        """Test getting control evidence."""
        mock_evidence_class.get_by_control.return_value = [mock_evidence]

        result = DatabaseOperations.get_control_evidence("test-control-id")

        assert result == [mock_evidence]
        mock_evidence_class.get_by_control.assert_called_once_with("test-control-id")

    @patch("app.database.operations.SecurityAssessment")
    def test_get_assessments_by_status(
        self, mock_assessment_class: MagicMock, mock_assessment: MagicMock
    ) -> None:
        """Test getting assessments by status."""
        mock_assessment.status = "prepare"
        mock_assessment_class.scan.return_value = [mock_assessment]

        result = DatabaseOperations.get_assessments_by_status("prepare")

        assert len(result) == 1
        assert result[0].status == "prepare"

    @patch("app.database.operations.Control")
    def test_get_controls_by_nist_id(
        self, mock_control_class: MagicMock, mock_control: MagicMock
    ) -> None:
        """Test getting controls by NIST ID."""
        mock_control.nist_control_id = "AC-1"
        mock_control_class.scan.return_value = [mock_control]

        result = DatabaseOperations.get_controls_by_nist_id("AC-1")

        assert len(result) == 1
        assert result[0].nist_control_id == "AC-1"

    @patch("app.database.operations.Evidence")
    def test_get_recent_evidence_for_control(
        self, mock_evidence_class: MagicMock, mock_evidence: MagicMock
    ) -> None:
        """Test getting recent evidence for control."""
        mock_evidence_class.get_recent_evidence.return_value = [mock_evidence]

        result = DatabaseOperations.get_recent_evidence_for_control(
            "test-control-id", limit=5
        )

        assert result == [mock_evidence]
        mock_evidence_class.get_recent_evidence.assert_called_once_with(
            "test-control-id", 5
        )

    @patch("app.database.operations.SecurityAssessment")
    @patch("app.database.operations.User")
    def test_create_user_and_assessment_new_user(
        self,
        mock_user_class: MagicMock,
        mock_assessment_class: MagicMock,
        mock_user: MagicMock,
        mock_assessment: MagicMock,
    ) -> None:
        """Test creating new user and assessment."""
        mock_user_class.get_by_google_id.return_value = None
        mock_user_class.create_user.return_value = mock_user
        mock_assessment_class.create_assessment.return_value = mock_assessment

        result = DatabaseOperations.create_user_and_assessment(
            google_id="google-id",
            email="test@example.com",
            name="Test User",
            product_name="Product",
            product_description="Description",
        )

        assert result["user"] == mock_user
        assert result["assessment"] == mock_assessment
        mock_user_class.create_user.assert_called_once()

    @patch("app.database.operations.SecurityAssessment")
    @patch("app.database.operations.User")
    def test_create_user_and_assessment_existing_user(
        self,
        mock_user_class: MagicMock,
        mock_assessment_class: MagicMock,
        mock_user: MagicMock,
        mock_assessment: MagicMock,
    ) -> None:
        """Test creating assessment for existing user."""
        mock_user_class.get_by_google_id.return_value = mock_user
        mock_assessment_class.create_assessment.return_value = mock_assessment

        result = DatabaseOperations.create_user_and_assessment(
            google_id="google-id",
            email="test@example.com",
            name="Test User",
            product_name="Product",
            product_description="Description",
        )

        assert result["user"] == mock_user
        assert result["assessment"] == mock_assessment
        mock_user_class.create_user.assert_not_called()

    @patch("app.database.operations.Control")
    @patch("app.database.operations.SecurityAssessment")
    def test_get_assessment_summary_success(
        self,
        mock_assessment_class: MagicMock,
        mock_control_class: MagicMock,
        mock_assessment: MagicMock,
        mock_control: MagicMock,
    ) -> None:
        """Test getting assessment summary successfully."""
        mock_assessment_class.get.return_value = mock_assessment
        mock_assessment.is_owner.return_value = True
        mock_control_class.get_by_assessment.return_value = [mock_control]
        mock_control.status = "compliant"

        with patch.object(DatabaseOperations, "get_control_evidence", return_value=[]):
            result = DatabaseOperations.get_assessment_summary(
                "test-assessment-id", "test-user-id"
            )

            assert result is not None
            assert result["assessment"] == mock_assessment
            assert result["total_controls"] == 1

    @patch("app.database.operations.SecurityAssessment")
    def test_get_assessment_summary_no_access(
        self, mock_assessment_class: MagicMock, mock_assessment: MagicMock
    ) -> None:
        """Test getting assessment summary without access."""
        mock_assessment_class.get.return_value = mock_assessment
        mock_assessment.is_owner.return_value = False

        result = DatabaseOperations.get_assessment_summary(
            "test-assessment-id", "different-user-id"
        )

        assert result is None

    @patch("app.database.operations.Evidence")
    @patch("app.database.operations.Control")
    def test_add_control_with_evidence(
        self,
        mock_control_class: MagicMock,
        mock_evidence_class: MagicMock,
        mock_control: MagicMock,
        mock_evidence: MagicMock,
    ) -> None:
        """Test adding control with evidence."""
        mock_control_class.create_control.return_value = mock_control
        mock_evidence_class.create_evidence.return_value = mock_evidence

        evidence_items = [
            {
                "title": "Evidence 1",
                "description": "Description",
                "evidence_type": "document",
            }
        ]

        with patch.object(
            DatabaseOperations, "check_user_assessment_access", return_value=True
        ):
            result = DatabaseOperations.add_control_with_evidence(
                assessment_id="test-assessment-id",
                user_id="test-user-id",
                nist_control_id="AC-1",
                control_title="Access Control",
                control_description="Description",
                evidence_items=evidence_items,
            )

            assert result is not None
            assert result["control"] == mock_control
            assert len(result["evidence"]) == 1

    @patch("app.database.operations.Control")
    def test_add_control_with_evidence_no_access(
        self, mock_control_class: MagicMock
    ) -> None:
        """Test adding control without access."""
        with patch.object(
            DatabaseOperations, "check_user_assessment_access", return_value=False
        ):
            result = DatabaseOperations.add_control_with_evidence(
                assessment_id="test-assessment-id",
                user_id="different-user-id",
                nist_control_id="AC-1",
                control_title="Access Control",
                control_description="Description",
            )

            assert result is None
            mock_control_class.create_control.assert_not_called()
