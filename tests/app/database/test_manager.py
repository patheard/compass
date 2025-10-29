"""Unit tests for database manager."""

import os
from unittest.mock import MagicMock, patch

import pytest

from app.database.manager import DatabaseManager


class TestDatabaseManager:
    """Tests for DatabaseManager class."""

    def test_get_all_models(self) -> None:
        """Test getting all database models."""
        models = DatabaseManager.get_all_models()

        assert len(models) == 7
        assert all(hasattr(model, "get_table_name") for model in models)

    @patch("app.database.manager.User")
    @patch("app.database.manager.SecurityAssessment")
    @patch("app.database.manager.Control")
    @patch("app.database.manager.Evidence")
    @patch("app.database.manager.JobTemplate")
    @patch("app.database.manager.JobExecution")
    @patch("app.database.manager.ChatSessionMessage")
    def test_initialize_tables_creates_new_tables(
        self,
        mock_chat: MagicMock,
        mock_job_exec: MagicMock,
        mock_job_template: MagicMock,
        mock_evidence: MagicMock,
        mock_control: MagicMock,
        mock_assessment: MagicMock,
        mock_user: MagicMock,
    ) -> None:
        """Test initializing tables creates new tables."""
        models = [
            mock_user,
            mock_assessment,
            mock_control,
            mock_evidence,
            mock_job_template,
            mock_job_exec,
            mock_chat,
        ]

        for mock_model in models:
            mock_model.exists.return_value = False
            mock_model.get_table_name.return_value = "test-table"

        with patch.object(DatabaseManager, "get_all_models", return_value=models):
            result = DatabaseManager.initialize_tables()

            assert result is True
            for mock_model in models:
                mock_model.create_table.assert_called_once()

    @patch("app.database.manager.User")
    def test_initialize_tables_skips_existing(self, mock_user: MagicMock) -> None:
        """Test initializing tables skips existing tables."""
        mock_user.exists.return_value = True
        mock_user.get_table_name.return_value = "test-table"

        with patch.object(DatabaseManager, "get_all_models", return_value=[mock_user]):
            result = DatabaseManager.initialize_tables()

            assert result is True
            mock_user.create_table.assert_not_called()

    @patch("app.database.manager.User")
    @patch.dict(os.environ, {"ENVIRONMENT": "local"})
    def test_initialize_tables_handles_errors_local(self, mock_user: MagicMock) -> None:
        """Test initializing tables handles errors in local environment."""
        mock_user.exists.return_value = False
        mock_user.get_table_name.return_value = "test-table"
        mock_user.create_table.side_effect = Exception("Create failed")

        with patch.object(DatabaseManager, "get_all_models", return_value=[mock_user]):
            result = DatabaseManager.initialize_tables()

            assert result is False

    @patch("app.database.manager.User")
    @patch.dict(os.environ, {"ENVIRONMENT": "production"})
    def test_initialize_tables_raises_in_production(self, mock_user: MagicMock) -> None:
        """Test initializing tables raises errors in production."""
        mock_user.exists.return_value = False
        mock_user.get_table_name.return_value = "test-table"
        mock_user.create_table.side_effect = Exception("Create failed")

        with patch.object(DatabaseManager, "get_all_models", return_value=[mock_user]):
            with pytest.raises(Exception, match="Create failed"):
                DatabaseManager.initialize_tables()

    @patch("app.database.manager.User")
    def test_check_table_health_all_healthy(self, mock_user: MagicMock) -> None:
        """Test checking table health when all tables are healthy."""
        mock_user.exists.return_value = True
        mock_user.get_table_name.return_value = "test-table"
        mock_user.describe_table.return_value = {}

        with patch.object(DatabaseManager, "get_all_models", return_value=[mock_user]):
            result = DatabaseManager.check_table_health()

            assert result is True
            mock_user.describe_table.assert_called_once()

    @patch("app.database.manager.User")
    def test_check_table_health_table_missing(self, mock_user: MagicMock) -> None:
        """Test checking table health when table doesn't exist."""
        mock_user.exists.return_value = False
        mock_user.get_table_name.return_value = "test-table"

        with patch.object(DatabaseManager, "get_all_models", return_value=[mock_user]):
            result = DatabaseManager.check_table_health()

            assert result is False

    @patch("app.database.manager.User")
    def test_check_table_health_describe_fails(self, mock_user: MagicMock) -> None:
        """Test checking table health when describe fails."""
        mock_user.exists.return_value = True
        mock_user.get_table_name.return_value = "test-table"
        mock_user.describe_table.side_effect = Exception("Describe failed")

        with patch.object(DatabaseManager, "get_all_models", return_value=[mock_user]):
            result = DatabaseManager.check_table_health()

            assert result is False

    @patch("app.database.manager.User")
    @patch.dict(os.environ, {"ENVIRONMENT": "local"})
    def test_delete_all_tables_local(self, mock_user: MagicMock) -> None:
        """Test deleting all tables in local environment."""
        mock_user.exists.return_value = True
        mock_user.get_table_name.return_value = "test-table"

        with patch.object(DatabaseManager, "get_all_models", return_value=[mock_user]):
            DatabaseManager.delete_all_tables()

            mock_user.delete_table.assert_called_once()

    @patch("app.database.manager.User")
    @patch.dict(os.environ, {"ENVIRONMENT": "production"})
    def test_delete_all_tables_production_blocked(self, mock_user: MagicMock) -> None:
        """Test deleting all tables is blocked in production."""
        with patch.object(DatabaseManager, "get_all_models", return_value=[mock_user]):
            with pytest.raises(
                RuntimeError, match="Cannot delete tables in production"
            ):
                DatabaseManager.delete_all_tables()

            mock_user.delete_table.assert_not_called()

    @patch("app.database.manager.User")
    @patch.dict(os.environ, {"ENVIRONMENT": "local"})
    def test_delete_all_tables_skips_nonexistent(self, mock_user: MagicMock) -> None:
        """Test deleting all tables skips nonexistent tables."""
        mock_user.exists.return_value = False
        mock_user.get_table_name.return_value = "test-table"

        with patch.object(DatabaseManager, "get_all_models", return_value=[mock_user]):
            DatabaseManager.delete_all_tables()

            mock_user.delete_table.assert_not_called()

    @patch("app.database.manager.User")
    @patch.dict(os.environ, {"ENVIRONMENT": "local"})
    def test_delete_all_tables_raises_on_error(self, mock_user: MagicMock) -> None:
        """Test deleting all tables raises on error."""
        mock_user.exists.return_value = True
        mock_user.get_table_name.return_value = "test-table"
        mock_user.delete_table.side_effect = Exception("Delete failed")

        with patch.object(DatabaseManager, "get_all_models", return_value=[mock_user]):
            with pytest.raises(Exception, match="Delete failed"):
                DatabaseManager.delete_all_tables()
