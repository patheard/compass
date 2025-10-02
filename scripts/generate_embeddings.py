#!/usr/bin/env python3
"""
Generate embeddings for files using Azure OpenAI and store them in S3 Vector bucket.

This script walks a directory recursively, chunks large files, generates embeddings
using Azure OpenAI, and stores them in an S3 Vector bucket with metadata.
"""

import argparse
import hashlib
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import boto3
from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter
from openai import AzureOpenAI

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


class FileProcessor:
    """Process files and generate embeddings."""

    def __init__(
        self,
        config: Config,
        openai_client: AzureOpenAI,
        s3_client: Any,
        dry_run: bool = False,
    ):
        """Initialize file processor.

        Args:
            config: Configuration object
            openai_client: Azure OpenAI client
            s3_client: boto3 S3 Vectors client
            dry_run: If True, skip S3 uploads
        """
        self.config = config
        self.openai_client = openai_client
        self.s3_client = s3_client
        self.dry_run = dry_run

        # Statistics
        self.stats = {
            "files_discovered": 0,
            "files_processed": 0,
            "files_skipped": 0,
            "chunks_created": 0,
            "vectors_uploaded": 0,
            "failures": 0,
        }

    def is_binary_file(self, file_path: Path) -> bool:
        """Check if a file is binary by reading the first 4KB.

        Args:
            file_path: Path to the file to check

        Returns:
            True if file appears to be binary, False otherwise
        """
        try:
            with open(file_path, "rb") as f:
                chunk = f.read(4096)
                return b"\x00" in chunk
        except Exception as e:
            logger.warning(f"Error checking if {file_path} is binary: {e}")
            return True

    def should_process_file(
        self,
        file_path: Path,
        include_pattern: str | None,
        exclude_pattern: str | None,
    ) -> bool:
        """Determine if a file should be processed.

        Args:
            file_path: Path to the file
            include_pattern: Optional glob pattern for files to include
            exclude_pattern: Optional glob pattern for files to exclude

        Returns:
            True if file should be processed, False otherwise
        """
        # Check include pattern
        if include_pattern and not file_path.match(include_pattern):
            return False

        # Check exclude pattern
        if exclude_pattern and file_path.match(exclude_pattern):
            return False

        # Skip binary files
        if self.is_binary_file(file_path):
            logger.debug(f"Skipping binary file: {file_path}")
            return False

        # Skip empty files
        if file_path.stat().st_size == 0:
            logger.debug(f"Skipping empty file: {file_path}")
            return False

        # Skip dependency files
        if (
            "node_modules" in file_path.parts
            or "__pycache__" in file_path.parts
            or ".terragrunt-cache" in file_path.parts
        ):
            logger.debug(f"Skipping dependency file: {file_path}")
            return False

        # Skip env var files
        if ".env" in file_path.name or ".tfvars" in file_path.name:
            logger.debug(f"Skipping env var file: {file_path}")
            return False

        return True

    def chunk_text(self, text: str) -> list[str]:
        """Split text into overlapping chunks.

        Args:
            text: Text to chunk

        Returns:
            List of text chunks
        """
        if len(text) <= self.config.chunk_size:
            return [text]

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
            length_function=len,
        )

        chunks = splitter.split_text(text)
        return chunks

    def generate_chunk_id(
        self,
        file_path: Path,
        chunk_index: int,
        processed_at: str,
    ) -> str:
        """Generate deterministic ID for a chunk.

        Args:
            file_path: Path to the source file
            chunk_index: Index of the chunk
            processed_at: Processing timestamp

        Returns:
            SHA256 hash as hex string
        """
        content = f"{file_path}:{chunk_index}:{processed_at}"
        return hashlib.sha256(content.encode()).hexdigest()

    def generate_content_hash(self, text: str) -> str:
        """Generate SHA256 hash of chunk text.

        Args:
            text: Text to hash

        Returns:
            SHA256 hash as hex string
        """
        return hashlib.sha256(text.encode()).hexdigest()

    def get_type_from_extension(self, extension: str) -> str:
        """Map file extension to type.

        Args:
            extension: File extension (e.g., '.txt')

        Returns:
            Type string (e.g., 'text', 'code', 'markdown', 'unknown')
        """
        mapping = {
            ".txt": "text",
            ".md": "text",
            ".py": "code",
            ".js": "code",
            ".cs": "code",
            ".html": "code",
            ".css": "code",
            ".json": "code",
            ".xml": "configuration",
            ".yml": "configuration",
            ".yaml": "configuration",
            ".tf": "terraform",
        }
        return mapping.get(extension.lower(), "unknown")

    def get_embedding_with_retry(
        self,
        text: str,
        max_retries: int = 3,
    ) -> list[float] | None:
        """Get embedding from Azure OpenAI with exponential backoff retry.

        Args:
            text: Text to embed
            max_retries: Maximum number of retry attempts

        Returns:
            Embedding vector or None if all retries fail
        """
        for attempt in range(max_retries):
            try:
                response = self.openai_client.embeddings.create(
                    input=text,
                    model=self.config.azure_openai_embeddings_model,
                )
                return response.data[0].embedding
            except Exception as e:
                wait_time = 2**attempt  # Exponential backoff: 1, 2, 4 seconds
                logger.warning(
                    f"Embedding API call failed (attempt {attempt + 1}/{max_retries}): {e}"
                )
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error("All retry attempts failed for text chunk")
                    return None
        return None

    def store_vector_in_s3(
        self,
        vector_id: str,
        vector: list[float],
        metadata: dict[str, Any],
    ) -> bool:
        """Store vector in S3 Vector bucket.

        Args:
            vector_id: Unique identifier for the vector
            vector: Embedding vector
            metadata: Metadata dictionary

        Returns:
            True if successful, False otherwise
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Would upload vector {vector_id}")
            return True

        try:
            self.s3_client.put_vectors(
                vectorBucketName=self.config.s3_vector_bucket_name,
                indexName=self.config.s3_vector_index_name,
                vectors=[
                    {
                        "key": vector_id,
                        "data": {"float32": vector},
                        "metadata": metadata,
                    }
                ],
            )

            logger.debug(f"Uploaded vector {vector_id} to S3 Vectors")
            return True
        except Exception as e:
            logger.error(f"Failed to upload vector {vector_id} to S3 Vectors: {e}")
            return False

    def process_file(self, file_path: Path) -> bool:
        """Process a single file: chunk, embed, and store.

        Args:
            file_path: Path to the file to process

        Returns:
            True if successfully processed, False otherwise
        """
        try:
            logger.info(f"Processing file: {file_path}")

            # Read file content
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            # Get file metadata
            file_extension = file_path.suffix.lower()
            processed_at = datetime.now(timezone.utc).isoformat()

            # Chunk the content
            chunks = self.chunk_text(content)
            total_chunks = len(chunks)
            self.stats["chunks_created"] += total_chunks

            logger.info(f"Split into {total_chunks} chunks")

            # Process each chunk
            success = True
            for chunk_index, chunk_text in enumerate(chunks):
                # Generate embedding
                embedding = self.get_embedding_with_retry(chunk_text)
                if embedding is None:
                    logger.error(
                        f"Failed to generate embedding for {file_path} chunk {chunk_index}"
                    )
                    self.stats["failures"] += 1
                    success = False
                    continue

                # Create metadata
                metadata = {
                    "file_path": str(file_path.absolute()),
                    "file_name": file_path.name,
                    "file_extension": file_extension,
                    "chunk_index": chunk_index,
                    "chunk_text": chunk_text,
                    "type": self.get_type_from_extension(file_extension),
                }

                # Generate chunk ID
                chunk_id = self.generate_chunk_id(file_path, chunk_index, processed_at)

                # Store in S3
                if self.store_vector_in_s3(chunk_id, embedding, metadata):
                    self.stats["vectors_uploaded"] += 1
                else:
                    self.stats["failures"] += 1
                    success = False

            return success

        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            self.stats["failures"] += 1
            return False

    def process_directory(
        self,
        input_folder: Path,
        max_files: int | None = None,
        include_pattern: str | None = None,
        exclude_pattern: str | None = None,
    ):
        """Process all files in a directory recursively.

        Args:
            input_folder: Root directory to process
            max_files: Optional limit on number of files to process
            include_pattern: Optional glob pattern for files to include
            exclude_pattern: Optional glob pattern for files to exclude
        """
        logger.info(f"Scanning directory: {input_folder}")

        # Collect all files
        all_files = []
        for file_path in input_folder.rglob("*"):
            if file_path.is_file():
                all_files.append(file_path)

        self.stats["files_discovered"] = len(all_files)
        logger.info(f"Discovered {len(all_files)} files")

        # Apply max_files limit
        if max_files:
            all_files = all_files[:max_files]
            logger.info(f"Limited to {len(all_files)} files (max_files={max_files})")

        # Process each file
        for file_path in all_files:
            if self.should_process_file(file_path, include_pattern, exclude_pattern):
                if self.process_file(file_path):
                    self.stats["files_processed"] += 1
                else:
                    self.stats["files_skipped"] += 1
            else:
                self.stats["files_skipped"] += 1

        # Print summary
        self.print_summary()

    def print_summary(self):
        """Print processing summary statistics."""
        logger.info("=" * 80)
        logger.info("PROCESSING SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Files discovered:  {self.stats['files_discovered']}")
        logger.info(f"Files processed:   {self.stats['files_processed']}")
        logger.info(f"Files skipped:     {self.stats['files_skipped']}")
        logger.info(f"Chunks created:    {self.stats['chunks_created']}")
        logger.info(f"Vectors uploaded:  {self.stats['vectors_uploaded']}")
        logger.info(f"Failures:          {self.stats['failures']}")
        logger.info("=" * 80)


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

    # Process files
    processor = FileProcessor(config, openai_client, s3_client, args.dry_run)
    processor.process_directory(
        input_folder,
        max_files=args.max_files,
        include_pattern=args.include,
        exclude_pattern=args.exclude,
    )

    logger.info("Embedding generation complete")


if __name__ == "__main__":
    main()
