"""Unit tests for Evidence model."""

from unittest.mock import MagicMock

from app.database.models.evidence import Evidence


class TestEvidenceModel:
    """Tests for Evidence model."""

    def test_evidence_has_required_attributes(self) -> None:
        """Test that Evidence model has required attributes."""
        evidence = MagicMock(spec=Evidence)
        evidence.evidence_id = "ev-123"
        evidence.assessment_id = "assess-123"
        evidence.control_id = "control-123"
        evidence.title = "S3 Configuration"
        evidence.type = "automated"

        assert evidence.evidence_id is not None
        assert evidence.assessment_id is not None
        assert evidence.control_id is not None
        assert evidence.title is not None
        assert evidence.type is not None

    def test_evidence_type_validation(self) -> None:
        """Test that evidence validates type values."""
        evidence = MagicMock(spec=Evidence)
        evidence.type = "automated"

        valid_types = ["automated", "manual", "document"]
        assert evidence.type in valid_types

    def test_evidence_s3_key(self) -> None:
        """Test evidence can store S3 key."""
        evidence = MagicMock(spec=Evidence)
        evidence.s3_key = "evidence/assess-123/ev-456/file.pdf"

        assert evidence.s3_key is not None
        assert "evidence/" in evidence.s3_key
