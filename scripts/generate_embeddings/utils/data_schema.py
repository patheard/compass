#!/usr/bin/env python3
"""
Data schema documentation for the shared store used in the embedding generation flow.

The shared store is a dictionary that all nodes read from and write to.
This document describes the structure and conventions.
"""

from typing import TypedDict, Any
from pathlib import Path


class ChunkData(TypedDict):
    """Data for a single text chunk."""

    chunk_text: str
    chunk_index: int
    source_file: str
    file_extension: str
    type: str


class FileData(TypedDict):
    """Data for a file to be processed."""

    file_path: Path
    content: str | None


class ModuleReference(TypedDict):
    """Data for a detected Terraform module."""

    name: str
    source: str
    detected_in_file: str
    detected_in_chunk: int


class SharedStore(TypedDict):
    """
    The shared store structure used across all nodes.

    Structure:
    {
        # Configuration (set at initialization)
        "config": {
            "chunk_size": int,
            "chunk_overlap": int,
            "dry_run": bool,
            "include_pattern": str | None,
            "exclude_pattern": str | None,
            "max_files": int | None,
        },

        # Clients (set at initialization)
        "clients": {
            "openai": AzureOpenAI,
            "s3": boto3.client,
        },

        # File discovery
        "all_files": [Path, Path, ...],  # All discovered files
        "filtered_files": [Path, Path, ...],  # Files after filtering

        # File processing
        "files_to_process": [
            {
                "file_path": Path,
                "content": str,
            },
            ...
        ],

        # Chunking
        "chunks": [
            {
                "chunk_text": str,
                "chunk_index": int,
                "source_file": str,
                "file_extension": str,
                "type": str,  # "code", "text", "configuration", etc.
            },
            ...
        ],

        # Terraform module detection
        "terraform_modules": [
            {
                "name": str,
                "source": str,
                "detected_in_file": str,
                "detected_in_chunk": int,
            },
            ...
        ],

        "downloaded_modules": {
            "module_source": Path,  # Path to downloaded module directory
            ...
        },

        "module_files_to_process": [
            {
                "file_path": Path,
                "content": str,
                "from_module": str,  # Module source
            },
            ...
        ],

        # Statistics (updated throughout processing)
        "stats": {
            "files_discovered": int,
            "files_processed": int,
            "files_skipped": int,
            "chunks_created": int,
            "vectors_uploaded": int,
            "terraform_modules_detected": int,
            "terraform_modules_downloaded": int,
            "failures": int,
        },

        # Processed at timestamp (set at start)
        "processed_at": str,  # ISO 8601 timestamp
    }
    """

    pass


# Example initialization
def create_shared_store(config: dict[str, Any], clients: dict[str, Any]) -> dict:
    """Create an initialized shared store.

    Args:
        config: Configuration dictionary
        clients: Clients dictionary (openai, s3)

    Returns:
        Initialized shared store
    """
    from datetime import datetime, timezone

    return {
        "config": config,
        "clients": clients,
        "all_files": [],
        "filtered_files": [],
        "files_to_process": [],
        "chunks": [],
        "terraform_modules": [],
        "downloaded_modules": {},
        "module_files_to_process": [],
        "stats": {
            "files_discovered": 0,
            "files_processed": 0,
            "files_skipped": 0,
            "chunks_created": 0,
            "vectors_uploaded": 0,
            "terraform_modules_detected": 0,
            "terraform_modules_downloaded": 0,
            "failures": 0,
        },
        "processed_at": datetime.now(timezone.utc).isoformat(),
    }
