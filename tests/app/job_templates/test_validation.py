"""Unit tests for job template validation."""

import pytest

from app.job_templates.validation import JobTemplateRequest


class TestJobTemplateRequest:
    """Tests for JobTemplateRequest validation."""

    def test_valid_request_with_all_fields(self) -> None:
        """Test validation with all fields provided."""
        data = JobTemplateRequest(
            name="Test Template",
            description="Test description",
            scan_type="aws_config",
            config='{"key": "value"}',
            aws_resources=["s3"],
            nist_control_ids=["AC-6"],
        )

        assert data.name == "Test Template"
        assert data.description == "Test description"
        assert data.scan_type == "aws_config"
        assert data.config == {"key": "value"}
        assert data.aws_resources == ["s3"]
        assert data.nist_control_ids == ["AC-6"]

    def test_valid_request_with_minimal_fields(self) -> None:
        """Test validation with only required fields."""
        data = JobTemplateRequest(
            name="Test Template",
            description="Test description",
            scan_type="aws_config",
            config='{"key": "value"}',
        )

        assert data.name == "Test Template"
        assert data.description == "Test description"
        assert data.scan_type == "aws_config"
        assert data.config == {"key": "value"}
        assert data.aws_resources is None
        assert data.nist_control_ids is None

    def test_validate_name_empty_string(self) -> None:
        """Test that empty name is rejected."""
        with pytest.raises(ValueError):
            JobTemplateRequest(
                name="   ",
                description="Test description",
                scan_type="aws_config",
                config='{"key": "value"}',
            )

    def test_validate_description_empty_string(self) -> None:
        """Test that empty description is rejected."""
        with pytest.raises(ValueError):
            JobTemplateRequest(
                name="Test Template",
                description="   ",
                scan_type="aws_config",
                config='{"key": "value"}',
            )

    def test_validate_scan_type_invalid(self) -> None:
        """Test that invalid scan type is rejected."""
        with pytest.raises(ValueError, match="Scan type must be one of"):
            JobTemplateRequest(
                name="Test Template",
                description="Test description",
                scan_type="invalid_type",
                config='{"key": "value"}',
            )

    def test_validate_config_as_json_string(self) -> None:
        """Test that config as JSON string is parsed."""
        data = JobTemplateRequest(
            name="Test Template",
            description="Test description",
            scan_type="aws_config",
            config='{"key": "value"}',
        )

        assert data.config == {"key": "value"}

    def test_validate_config_empty_string(self) -> None:
        """Test that empty config string is rejected."""
        with pytest.raises(ValueError, match="Config cannot be an empty"):
            JobTemplateRequest(
                name="Test Template",
                description="Test description",
                scan_type="aws_config",
                config="   ",
            )

    def test_validate_config_invalid_json(self) -> None:
        """Test that invalid JSON config is rejected."""
        with pytest.raises(ValueError, match="Config is not valid JSON"):
            JobTemplateRequest(
                name="Test Template",
                description="Test description",
                scan_type="aws_config",
                config="not valid json",
            )

    def test_validate_config_none(self) -> None:
        """Test that None config is accepted."""
        data = JobTemplateRequest(
            name="Test Template",
            description="Test description",
            scan_type="aws_config",
            config=None,
        )

        assert data.config is None

    def test_validate_aws_resources_invalid(self) -> None:
        """Test that invalid AWS resources are rejected."""
        with pytest.raises(ValueError, match="AWS resources contains invalid entries"):
            JobTemplateRequest(
                name="Test Template",
                description="Test description",
                scan_type="aws_config",
                config='{"key": "value"}',
                aws_resources=["Invalid::Resource"],
            )

    def test_validate_aws_resources_none(self) -> None:
        """Test that None AWS resources is accepted."""
        data = JobTemplateRequest(
            name="Test Template",
            description="Test description",
            scan_type="aws_config",
            config='{"key": "value"}',
            aws_resources=None,
        )

        assert data.aws_resources is None

    def test_validate_nist_control_ids_invalid(self) -> None:
        """Test that invalid NIST control IDs are rejected."""
        with pytest.raises(
            ValueError, match="NIST control IDs contains invalid entries"
        ):
            JobTemplateRequest(
                name="Test Template",
                description="Test description",
                scan_type="aws_config",
                config='{"key": "value"}',
                nist_control_ids=["INVALID-ID"],
            )

    def test_config_html_escaped(self) -> None:
        """Test that HTML in config string is unescaped before parsing."""
        data = JobTemplateRequest(
            name="Test Template",
            description="Test description",
            scan_type="aws_config",
            config='{"message": "Hello World"}',
        )

        assert data.config == {"message": "Hello World"}
