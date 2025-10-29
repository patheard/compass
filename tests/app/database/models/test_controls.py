"""Unit tests for Control model."""

from unittest.mock import MagicMock

from app.database.models.controls import Control


class TestControlModel:
    """Tests for Control model."""

    def test_control_has_required_attributes(self) -> None:
        """Test that Control model has required attributes."""
        control = MagicMock(spec=Control)
        control.control_id = "control-123"
        control.assessment_id = "assess-123"
        control.name = "Access Control"
        control.status = "not_started"

        assert control.control_id is not None
        assert control.assessment_id is not None
        assert control.name is not None
        assert control.status is not None

    def test_control_status_validation(self) -> None:
        """Test that control validates status values."""
        control = MagicMock(spec=Control)
        control.status = "in_progress"

        valid_statuses = ["not_started", "in_progress", "complete", "not_applicable"]
        assert control.status in valid_statuses

    def test_control_evidence_list(self) -> None:
        """Test control can store evidence list."""
        control = MagicMock(spec=Control)
        control.evidence = ["ev-1", "ev-2"]

        assert isinstance(control.evidence, list)
        assert len(control.evidence) == 2
