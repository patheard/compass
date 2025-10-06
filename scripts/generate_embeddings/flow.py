#!/usr/bin/env python3
"""
PocketFlow flows for the embedding generation system.
"""

import logging
from sys import path as sys_path

# Add PocketFlow to path
sys_path.insert(0, "/Users/patrick.heard/dev/util/PocketFlow")

from pocketflow import Flow

from nodes import (
    DiscoverFilesNode,
    FilterFilesNode,
    ReadFilesNode,
    ChunkFilesNode,
    DetectTerraformModulesNode,
    DownloadModulesNode,
    ProcessModuleFilesNode,
    ChunkModuleFilesNode,
    GenerateEmbeddingsNode,
    StoreVectorsNode,
    PrintSummaryNode,
)

logger = logging.getLogger(__name__)


def create_module_processing_flow():
    """Create a flow for processing Terraform modules.

    This flow:
    1. Downloads detected modules
    2. Processes their files
    3. Chunks the module files
    4. Returns to main flow for embedding generation

    Returns:
        Flow for module processing
    """
    download_modules = DownloadModulesNode()
    process_module_files = ProcessModuleFilesNode()
    chunk_module_files = ChunkModuleFilesNode()

    # Wire the nodes
    download_modules - "process_modules" >> process_module_files
    process_module_files - "process_module_content" >> chunk_module_files

    # Create the flow
    module_flow = Flow(start=download_modules)

    return module_flow


def create_main_flow():
    """Create the main embedding generation flow.

    This flow:
    1. Discovers files in the input directory
    2. Filters files based on patterns
    3. Reads file contents
    4. Chunks the text
    5. Detects Terraform modules
    6. (If modules found) Downloads and processes them
    7. Generates embeddings for all chunks
    8. Stores vectors in S3
    9. Prints summary

    Returns:
        Main processing flow
    """
    # Create nodes
    discover_files = DiscoverFilesNode()
    filter_files = FilterFilesNode()
    read_files = ReadFilesNode()
    chunk_files = ChunkFilesNode()
    detect_tf_modules = DetectTerraformModulesNode()
    generate_embeddings = GenerateEmbeddingsNode(max_retries=3)
    store_vectors = StoreVectorsNode()
    print_summary = PrintSummaryNode()

    # Create module processing sub-flow
    module_flow = create_module_processing_flow()

    # Wire the main flow
    discover_files >> filter_files >> read_files >> chunk_files

    # After chunking, detect Terraform modules
    chunk_files >> detect_tf_modules

    # If modules are detected, process them, then continue to embeddings
    detect_tf_modules - "download_modules" >> module_flow
    module_flow >> generate_embeddings

    # If no modules detected, go straight to embeddings
    detect_tf_modules - "default" >> generate_embeddings

    # Continue with embedding and storage
    generate_embeddings >> store_vectors >> print_summary

    # Create the main flow
    main_flow = Flow(start=discover_files)

    return main_flow


if __name__ == "__main__":
    # Visualize the flow structure
    print("Main Flow Structure:")
    print("=" * 80)
    print(
        """
    DiscoverFiles
        ↓
    FilterFiles
        ↓
    ReadFiles
        ↓
    ChunkFiles
        ↓
    DetectTerraformModules
        ↓ (if modules found)
        ├─→ DownloadModules
        │       ↓
        │   ProcessModuleFiles
        │       ↓
        │   ChunkModuleFiles
        │       ↓
        └─→ GenerateEmbeddings
                ↓
            StoreVectors
                ↓
            PrintSummary
    """
    )
    print("=" * 80)
