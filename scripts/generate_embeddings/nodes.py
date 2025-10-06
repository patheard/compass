#!/usr/bin/env python3
"""
PocketFlow nodes for the embedding generation system.
"""

import hashlib
import logging
import shutil
import tempfile
from pathlib import Path

from pocketflow import Node, BatchNode
from utils.azure_embedding import get_embedding
from utils.chunking import chunk_text
from utils.s3_storage import store_vector
from utils.terraform_module import (
    detect_terraform_modules,
    download_terraform_module,
    read_downloaded_module_files,
)

logger = logging.getLogger(__name__)


# ============================================================================
# File Discovery and Filtering Nodes
# ============================================================================


class DiscoverFilesNode(Node):
    """Discover all files in the input directory."""

    def prep(self, shared):
        """Get input folder from config."""
        return shared["config"]["input_folder"]

    def exec(self, input_folder):
        """Recursively find all files in the directory."""
        all_files = []
        for file_path in input_folder.rglob("*"):
            if file_path.is_file():
                all_files.append(file_path)
        logger.info(f"Discovered {len(all_files)} files")
        return all_files

    def post(self, shared, prep_res, exec_res):
        """Store discovered files in shared."""
        shared["all_files"] = exec_res
        shared["stats"]["files_discovered"] = len(exec_res)
        return "default"


class FilterFilesNode(BatchNode):
    """Filter files based on patterns and file type."""

    def prep(self, shared):
        """Get all files and filter patterns."""
        return shared["all_files"]

    def exec(self, file_path: Path):
        """Check if a single file should be processed."""
        config = self.params.get("config", {})
        include_pattern = config.get("include_pattern")
        exclude_pattern = config.get("exclude_pattern")

        # Check include pattern
        if include_pattern and not file_path.match(include_pattern):
            return None

        # Check exclude pattern
        if exclude_pattern and file_path.match(exclude_pattern):
            return None

        # Skip binary files
        if self._is_binary_file(file_path):
            logger.debug(f"Skipping binary file: {file_path}")
            return None

        # Skip empty files
        if file_path.stat().st_size == 0:
            logger.debug(f"Skipping empty file: {file_path}")
            return None

        # Skip dependency files
        if (
            "node_modules" in file_path.parts
            or "__pycache__" in file_path.parts
            or ".terragrunt-cache" in file_path.parts
        ):
            logger.debug(f"Skipping dependency file: {file_path}")
            return None

        # Skip env var files
        if ".env" in file_path.name or ".tfvars" in file_path.name:
            logger.debug(f"Skipping env var file: {file_path}")
            return None

        return file_path

    def post(self, shared, prep_res, exec_res_list):
        """Store filtered files."""
        # Filter out None values
        filtered = [f for f in exec_res_list if f is not None]

        # Apply max_files limit
        max_files = shared["config"].get("max_files")
        if max_files:
            filtered = filtered[:max_files]
            logger.info(f"Limited to {len(filtered)} files (max_files={max_files})")

        shared["filtered_files"] = filtered
        logger.info(f"Filtered to {len(filtered)} files for processing")
        return "default"

    def _is_binary_file(self, file_path: Path) -> bool:
        """Check if file is binary."""
        try:
            with open(file_path, "rb") as f:
                chunk = f.read(4096)
                return b"\x00" in chunk
        except Exception as e:
            logger.warning(f"Error checking if {file_path} is binary: {e}")
            return True


# ============================================================================
# File Reading and Chunking Nodes
# ============================================================================


class ReadFilesNode(BatchNode):
    """Read content from filtered files."""

    def prep(self, shared):
        """Get filtered files."""
        return shared["filtered_files"]

    def exec(self, file_path: Path):
        """Read a single file."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            logger.info(f"Read file: {file_path}")
            return {"file_path": file_path, "content": content}
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            return None

    def post(self, shared, prep_res, exec_res_list):
        """Store file data."""
        # Filter out failed reads
        files_data = [f for f in exec_res_list if f is not None]
        shared["files_to_process"] = files_data
        shared["stats"]["files_processed"] = len(files_data)
        shared["stats"]["files_skipped"] = len(prep_res) - len(files_data)
        return "default"


class ChunkFilesNode(BatchNode):
    """Chunk file contents into smaller pieces."""

    def prep(self, shared):
        """Get files to process."""
        return shared["files_to_process"]

    def exec(self, file_data: dict):
        """Chunk a single file's content."""
        file_path = file_data["file_path"]
        content = file_data["content"]
        config = self.params.get("config", {})

        # Chunk the text
        chunks = chunk_text(
            content,
            chunk_size=config.get("chunk_size", 1024),
            chunk_overlap=config.get("chunk_overlap", 100),
        )

        # Create chunk data
        file_extension = file_path.suffix.lower()
        chunk_objects = []

        for idx, text in enumerate(chunks):
            chunk_objects.append(
                {
                    "chunk_text": text,
                    "chunk_index": idx,
                    "source_file": str(file_path.absolute()),
                    "file_extension": file_extension,
                    "type": self._get_type_from_extension(file_extension),
                }
            )

        logger.info(f"Split {file_path} into {len(chunks)} chunks")
        return chunk_objects

    def post(self, shared, prep_res, exec_res_list):
        """Flatten and store all chunks."""
        # Flatten list of lists
        all_chunks = []
        for chunk_list in exec_res_list:
            all_chunks.extend(chunk_list)

        shared["chunks"] = all_chunks
        shared["stats"]["chunks_created"] = len(all_chunks)
        logger.info(f"Created {len(all_chunks)} total chunks")
        return "default"

    def _get_type_from_extension(self, extension: str) -> str:
        """Map file extension to type."""
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


# ============================================================================
# Embedding and Storage Nodes
# ============================================================================


class GenerateEmbeddingsNode(BatchNode):
    """Generate embeddings for all chunks."""

    def __init__(self, max_retries=3):
        """Initialize with retry support."""
        super().__init__(max_retries=max_retries)

    def prep(self, shared):
        """Get chunks to embed."""
        return shared["chunks"]

    def exec(self, chunk_data: dict):
        """Generate embedding for a single chunk."""
        clients = self.params.get("clients", {})
        config = self.params.get("config", {})

        embedding = get_embedding(
            chunk_data["chunk_text"],
            clients["openai"],
            config.get("embeddings_model"),
            max_retries=self.max_retries,
        )

        if embedding is None:
            logger.error(
                f"Failed to generate embedding for chunk {chunk_data['chunk_index']} "
                f"from {chunk_data['source_file']}"
            )
            return None

        return {"chunk_data": chunk_data, "embedding": embedding}

    def post(self, shared, prep_res, exec_res_list):
        """Store embeddings with chunks."""
        # Filter out failed embeddings
        successful = [e for e in exec_res_list if e is not None]

        # Update chunks with embeddings
        shared["chunks_with_embeddings"] = successful

        failures = len(prep_res) - len(successful)
        shared["stats"]["failures"] += failures

        logger.info(f"Generated {len(successful)} embeddings ({failures} failures)")
        return "default"


class StoreVectorsNode(BatchNode):
    """Store vectors in S3."""

    def prep(self, shared):
        """Get chunks with embeddings."""
        return shared.get("chunks_with_embeddings", [])

    def exec(self, chunk_with_embedding: dict):
        """Store a single vector."""
        chunk_data = chunk_with_embedding["chunk_data"]
        embedding = chunk_with_embedding["embedding"]

        clients = self.params.get("clients", {})
        config = self.params.get("config", {})
        processed_at = self.params.get("processed_at")

        # Generate chunk ID
        chunk_id = self._generate_chunk_id(
            chunk_data["source_file"],
            chunk_data["chunk_index"],
            processed_at,
        )

        # Create metadata
        metadata = {
            "file_path": chunk_data["source_file"],
            "file_name": Path(chunk_data["source_file"]).name,
            "file_extension": chunk_data["file_extension"],
            "chunk_index": chunk_data["chunk_index"],
            "chunk_text": chunk_data["chunk_text"],
            "type": chunk_data["type"],
        }

        # Store in S3
        success = store_vector(
            clients["s3"],
            config.get("s3_bucket_name"),
            config.get("s3_index_name"),
            chunk_id,
            embedding,
            metadata,
            dry_run=config.get("dry_run", False),
        )

        return success

    def post(self, shared, prep_res, exec_res_list):
        """Update statistics."""
        successful = sum(1 for r in exec_res_list if r)
        failed = len(exec_res_list) - successful

        shared["stats"]["vectors_uploaded"] = successful
        shared["stats"]["failures"] += failed

        logger.info(f"Stored {successful} vectors ({failed} failures)")
        return "default"

    def _generate_chunk_id(
        self, file_path: str, chunk_index: int, processed_at: str
    ) -> str:
        """Generate deterministic ID for a chunk."""
        content = f"{file_path}:{chunk_index}:{processed_at}"
        return hashlib.sha256(content.encode()).hexdigest()


# ============================================================================
# Terraform Module Detection and Download Nodes
# ============================================================================


class DetectTerraformModulesNode(BatchNode):
    """Detect Terraform modules in chunks."""

    def prep(self, shared):
        """Get all chunks."""
        return shared["chunks"]

    def exec(self, chunk_data: dict):
        """Detect modules in a single chunk."""
        modules = detect_terraform_modules(chunk_data["chunk_text"])

        if modules:
            logger.info(
                f"Detected {len(modules)} module(s) in {chunk_data['source_file']} "
                f"chunk {chunk_data['chunk_index']}"
            )

        # Add context to modules
        for mod in modules:
            mod["detected_in_file"] = chunk_data["source_file"]
            mod["detected_in_chunk"] = chunk_data["chunk_index"]

        return modules

    def post(self, shared, prep_res, exec_res_list):
        """Store detected modules."""
        # Flatten list of lists
        all_modules = []
        for module_list in exec_res_list:
            all_modules.extend(module_list)

        # Deduplicate by source (same module might be in multiple chunks)
        unique_modules = {}
        for mod in all_modules:
            if mod["source"] not in unique_modules:
                unique_modules[mod["source"]] = mod

        shared["terraform_modules"] = list(unique_modules.values())
        shared["stats"]["terraform_modules_detected"] = len(unique_modules)

        logger.info(f"Detected {len(unique_modules)} unique Terraform modules")

        if unique_modules:
            return "download_modules"  # Action to trigger module download
        else:
            return "default"  # Skip module download


class DownloadModulesNode(BatchNode):
    """Download Terraform modules."""

    def prep(self, shared):
        """Get detected modules."""
        return shared.get("terraform_modules", [])

    def exec(self, module_ref: dict):
        """Download a single module."""
        # Create temp directory for modules if not exists
        temp_dir = Path(tempfile.gettempdir()) / "terraform_modules"
        temp_dir.mkdir(exist_ok=True)

        # Remove old module dir if exists
        module_path = temp_dir / module_ref["name"]
        if module_path.exists():
            shutil.rmtree(module_path)

        # Download the module
        module_dir = download_terraform_module(
            module_ref["source"], temp_dir, module_ref["name"]
        )

        if module_dir:
            logger.info(f"Downloaded module '{module_ref['name']}' to {module_dir}")
            return {
                "module_source": module_ref["source"],
                "module_dir": module_dir,
            }
        else:
            logger.warning(f"Failed to download module: {module_ref['source']}")
            return None

    def post(self, shared, prep_res, exec_res_list):
        """Store downloaded module paths."""
        # Filter successful downloads
        successful = [m for m in exec_res_list if m is not None]

        downloaded_modules = {}
        for mod in successful:
            downloaded_modules[mod["module_source"]] = mod["module_dir"]

        shared["downloaded_modules"] = downloaded_modules
        shared["stats"]["terraform_modules_downloaded"] = len(downloaded_modules)

        logger.info(f"Downloaded {len(downloaded_modules)} modules")

        if downloaded_modules:
            return "process_modules"  # Action to process module files
        else:
            return "default"


class ProcessModuleFilesNode(Node):
    """Read files from downloaded modules and add them to processing queue."""

    def prep(self, shared):
        """Get downloaded modules."""
        return shared.get("downloaded_modules", {})

    def exec(self, downloaded_modules: dict):
        """Read all .tf files from downloaded modules."""
        all_module_files = []

        for module_source, module_dir in downloaded_modules.items():
            files = read_downloaded_module_files(module_dir)

            for file_path, content in files:
                all_module_files.append(
                    {
                        "file_path": file_path,
                        "content": content,
                        "from_module": module_source,
                    }
                )

            logger.info(f"Read {len(files)} files from module: {module_source}")

        return all_module_files

    def post(self, shared, prep_res, exec_res):
        """Store module files for processing."""
        shared["module_files_to_process"] = exec_res
        logger.info(f"Queued {len(exec_res)} module files for processing")

        if exec_res:
            return "process_module_content"  # Action to chunk and embed module files
        else:
            return "default"


class ChunkModuleFilesNode(BatchNode):
    """Chunk module file contents (similar to ChunkFilesNode)."""

    def prep(self, shared):
        """Get module files to process."""
        return shared.get("module_files_to_process", [])

    def exec(self, file_data: dict):
        """Chunk a single module file's content."""
        file_path = file_data["file_path"]
        content = file_data["content"]
        from_module = file_data["from_module"]
        config = self.params.get("config", {})

        # Chunk the text
        chunks = chunk_text(
            content,
            chunk_size=config.get("chunk_size", 1024),
            chunk_overlap=config.get("chunk_overlap", 100),
        )

        # Create chunk data
        file_extension = file_path.suffix.lower()
        chunk_objects = []

        for idx, text in enumerate(chunks):
            chunk_objects.append(
                {
                    "chunk_text": text,
                    "chunk_index": idx,
                    "source_file": str(file_path.absolute()),
                    "file_extension": file_extension,
                    "type": "terraform_module",
                    "from_module": from_module,
                }
            )

        logger.info(f"Split module file {file_path.name} into {len(chunks)} chunks")
        return chunk_objects

    def post(self, shared, prep_res, exec_res_list):
        """Add module chunks to the main chunks list."""
        # Flatten list of lists
        all_module_chunks = []
        for chunk_list in exec_res_list:
            all_module_chunks.extend(chunk_list)

        # Append to existing chunks
        shared["chunks"].extend(all_module_chunks)
        shared["stats"]["chunks_created"] += len(all_module_chunks)

        logger.info(f"Created {len(all_module_chunks)} chunks from module files")
        return "default"


# ============================================================================
# Summary Node
# ============================================================================


class PrintSummaryNode(Node):
    """Print processing summary statistics."""

    def prep(self, shared):
        """Get statistics."""
        return shared["stats"]

    def exec(self, stats):
        """Format summary."""
        summary = [
            "=" * 80,
            "PROCESSING SUMMARY",
            "=" * 80,
            f"Files discovered:        {stats['files_discovered']}",
            f"Files processed:         {stats['files_processed']}",
            f"Files skipped:           {stats['files_skipped']}",
            f"Chunks created:          {stats['chunks_created']}",
            f"Vectors uploaded:        {stats['vectors_uploaded']}",
            f"TF modules detected:     {stats.get('terraform_modules_detected', 0)}",
            f"TF modules downloaded:   {stats.get('terraform_modules_downloaded', 0)}",
            f"Failures:                {stats['failures']}",
            "=" * 80,
        ]
        return "\n".join(summary)

    def post(self, shared, prep_res, exec_res):
        """Print the summary."""
        logger.info("\n" + exec_res)
        return "default"
