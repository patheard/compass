#!/usr/bin/env python3
"""
Generate embeddings for files using Azure OpenAI and store them in S3 Vector bucket.

This script uses PocketFlow to orchestrate the embedding generation workflow:
1. Discovers and filters files in a directory
2. Chunks large files
3. Detects and downloads Terraform modules (if present)
4. Generates embeddings using Azure OpenAI
5. Stores vectors in S3 with metadata

The workflow uses PocketFlow nodes and flows for better modularity and error handling.
"""

import argparse
import logging
import os
import sys
from pathlib import Path

import boto3
from dotenv import load_dotenv
from openai import AzureOpenAI

from flow import create_main_flow
from utils.data_schema import create_shared_store

# Load environment variables from .env file if present
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)


class Config:
    """Configuration loaded from environment variables."""

    def __init__(self):
        """Initialize configuration from environment variables."""
        self.azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.azure_openai_api_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.azure_openai_api_version = os.getenv("AZURE_OPENAI_API_VERSION")
        self.azure_openai_embeddings_model = os.getenv("AZURE_OPENAI_EMBEDDINGS_MODEL")
        self.s3_vector_bucket_name = os.getenv("S3_VECTOR_BUCKET_NAME")
        self.s3_vector_index_name = os.getenv("S3_VECTOR_INDEX_NAME")
        self.s3_vector_region = os.getenv("S3_VECTOR_REGION")
        self.chunk_size = int(os.getenv("CHUNK_SIZE", "1024"))
        self.chunk_overlap = int(os.getenv("CHUNK_OVERLAP", "100"))
        self.log_level = os.getenv("LOG_LEVEL", "INFO")

    def validate(self) -> list[str]:
        """Validate required configuration values.

        Returns:
            List of error messages for missing/invalid config values.
        """
        errors = []
        if not self.azure_openai_endpoint:
            errors.append("AZURE_OPENAI_ENDPOINT is required")
        if not self.azure_openai_api_key:
            errors.append("azure_openai_api_key is required")
        if not self.azure_openai_api_version:
            errors.append("azure_openai_api_version is required")
        if not self.azure_openai_embeddings_model:
            errors.append("AZURE_OPENAI_EMBEDDINGS_MODEL is required")
        if not self.s3_vector_bucket_name:
            errors.append("S3_VECTOR_BUCKET_NAME is required")
        if not self.s3_vector_index_name:
            errors.append("S3_VECTOR_INDEX_NAME is required")
        if self.chunk_size <= 0:
            errors.append("CHUNK_SIZE must be positive")
        if self.chunk_overlap < 0:
            errors.append("CHUNK_OVERLAP must be non-negative")
        if self.chunk_overlap >= self.chunk_size:
            errors.append("CHUNK_OVERLAP must be less than CHUNK_SIZE")
        return errors

    def to_dict(self) -> dict:
        """Convert config to dictionary for shared store.

        Returns:
            Dictionary with all config values
        """
        return {
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "embeddings_model": self.azure_openai_embeddings_model,
            "s3_bucket_name": self.s3_vector_bucket_name,
            "s3_index_name": self.s3_vector_index_name,
        }


def setup_logging(log_level: str):
    """Configure logging.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Generate embeddings for files using Azure OpenAI and store in S3 Vector bucket"
    )
    parser.add_argument(
        "--input-folder",
        type=str,
        help="Path to the input folder (can also use INPUT_FOLDER env var)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Process files but skip S3 uploads",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        help="Process only the first N files (useful for testing)",
    )
    parser.add_argument(
        "--include",
        type=str,
        help="Glob pattern to include files (e.g., '*.py')",
    )
    parser.add_argument(
        "--exclude",
        type=str,
        help="Glob pattern to exclude files (e.g., '*.log')",
    )

    args = parser.parse_args()

    # Load configuration
    config = Config()
    setup_logging(config.log_level)

    # Validate configuration
    errors = config.validate()
    if errors:
        logger.error("Configuration errors:")
        for error in errors:
            logger.error(f"  - {error}")
        sys.exit(1)

    # Get input folder
    input_folder_str = args.input_folder or os.getenv("INPUT_FOLDER")
    if not input_folder_str:
        logger.error(
            "Input folder must be specified via --input-folder or INPUT_FOLDER env var"
        )
        sys.exit(1)

    input_folder = Path(input_folder_str)
    if not input_folder.exists():
        logger.error(f"Input folder does not exist: {input_folder}")
        sys.exit(1)
    if not input_folder.is_dir():
        logger.error(f"Input folder is not a directory: {input_folder}")
        sys.exit(1)

    logger.info("Starting embedding generation")
    logger.info(f"Input folder: {input_folder}")
    logger.info(f"Azure endpoint: {config.azure_openai_endpoint}")
    logger.info(f"Model: {config.azure_openai_embeddings_model}")
    logger.info(f"S3 bucket: {config.s3_vector_bucket_name}")
    logger.info(f"Chunk size: {config.chunk_size}")
    logger.info(f"Chunk overlap: {config.chunk_overlap}")
    logger.info(f"Dry run: {args.dry_run}")

    # Initialize Azure OpenAI client
    try:
        openai_client = AzureOpenAI(
            azure_endpoint=config.azure_openai_endpoint,
            api_key=config.azure_openai_api_key,
            api_version=config.azure_openai_api_version,
        )
    except Exception as e:
        logger.error(f"Failed to initialize Azure OpenAI client: {e}")
        sys.exit(1)

    # Initialize S3 Vectors client
    try:
        s3_client = boto3.client("s3vectors", region_name=config.s3_vector_region)
    except Exception as e:
        logger.error(f"Failed to initialize S3 Vectors client: {e}")
        sys.exit(1)

    # Create config dict for shared store
    config_dict = config.to_dict()
    config_dict.update(
        {
            "input_folder": input_folder,
            "dry_run": args.dry_run,
            "max_files": args.max_files,
            "include_pattern": args.include,
            "exclude_pattern": args.exclude,
        }
    )

    # Create clients dict
    clients = {
        "openai": openai_client,
        "s3": s3_client,
    }

    # Create shared store
    shared = create_shared_store(config_dict, clients)

    # Create and run the main flow
    try:
        main_flow = create_main_flow()

        # Set params for all nodes
        main_flow.set_params(
            {
                "config": config_dict,
                "clients": clients,
                "processed_at": shared["processed_at"],
            }
        )

        # Run the flow
        logger.info("Running embedding generation flow...")
        main_flow.run(shared)

        logger.info("Embedding generation complete")

    except Exception as e:
        logger.error(f"Error during flow execution: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
