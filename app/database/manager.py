"""Database initialization and management utilities."""

import logging
import os
from typing import List, Type

from app.database.base import BaseModel
from app.database.models import (
    Control,
    Evidence,
    SecurityAssessment,
    User,
    ScanJobTemplate,
    ScanJobExecution,
)

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Database management utilities for initialization and health checks."""

    @staticmethod
    def get_all_models() -> List[Type[BaseModel]]:
        """Get all database models."""
        return [
            User,
            SecurityAssessment,
            Control,
            Evidence,
            ScanJobTemplate,
            ScanJobExecution,
        ]

    @staticmethod
    def initialize_tables(wait_for_creation: bool = True) -> bool:
        """
        Initialize all database tables if they don't exist.

        Args:
            wait_for_creation: Whether to wait for table creation to complete

        Returns:
            True if all tables were successfully initialized
        """
        models = DatabaseManager.get_all_models()
        created_tables = []
        existing_tables = []
        failed_tables = []

        logger.info(f"Initializing tables for models: {models}")
        for model in models:
            try:
                table_name = model.get_table_name()

                if not model.exists():
                    logger.info(f"Creating table: {table_name}")
                    model.create_table(
                        read_capacity_units=5,
                        write_capacity_units=5,
                        wait=wait_for_creation,
                    )
                    created_tables.append(table_name)
                    logger.info(f"Successfully created table: {table_name}")
                else:
                    existing_tables.append(table_name)
                    logger.info(f"Table already exists: {table_name}")

            except Exception as e:
                failed_tables.append(table_name)
                logger.error(f"Failed to initialize table {table_name}: {e}")

                # In production, decide whether to fail fast or continue
                if os.getenv("ENVIRONMENT", "local") == "production":
                    raise e

        # Summary logging
        if created_tables:
            logger.info(
                f"Created {len(created_tables)} new tables: {', '.join(created_tables)}"
            )
        if existing_tables:
            logger.info(
                f"Found {len(existing_tables)} existing tables: {', '.join(existing_tables)}"
            )
        if failed_tables:
            logger.error(
                f"Failed to initialize {len(failed_tables)} tables: {', '.join(failed_tables)}"
            )
            return False

        logger.info("Database initialization completed successfully")
        return True

    @staticmethod
    def check_table_health() -> bool:
        """
        Check if all required tables exist and are accessible.

        Returns:
            True if all tables are healthy
        """
        models = DatabaseManager.get_all_models()
        healthy_tables = []
        unhealthy_tables = []

        for model in models:
            try:
                table_name = model.get_table_name()

                if model.exists():
                    # Additional health check: try to describe the table
                    model.describe_table()
                    healthy_tables.append(table_name)
                else:
                    unhealthy_tables.append(table_name)
                    logger.warning(f"Table does not exist: {table_name}")

            except Exception as e:
                unhealthy_tables.append(table_name)
                logger.error(f"Table health check failed for {table_name}: {e}")

        if unhealthy_tables:
            logger.error(f"Unhealthy tables detected: {', '.join(unhealthy_tables)}")
            return False

        logger.info(f"All {len(healthy_tables)} tables are healthy")
        return True

    @staticmethod
    def delete_all_tables() -> None:
        """
        Delete all tables. USE WITH EXTREME CAUTION!
        Only for development/testing environments.
        """
        environment = os.getenv("ENVIRONMENT", "local")
        if environment == "production":
            raise RuntimeError("Cannot delete tables in production environment")

        logger.warning("DELETING ALL TABLES - This action cannot be undone!")

        models = DatabaseManager.get_all_models()
        for model in models:
            try:
                table_name = model.get_table_name()
                if model.exists():
                    logger.warning(f"Deleting table: {table_name}")
                    model.delete_table()
                    logger.info(f"Deleted table: {table_name}")
                else:
                    logger.info(f"Table does not exist, skipping: {table_name}")
            except Exception as e:
                logger.error(f"Failed to delete table {table_name}: {e}")
                raise
