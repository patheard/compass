# Generate Embeddings Script (PocketFlow Implementation)

A PocketFlow-based Python application that uses Azure OpenAI to generate text embeddings for files in a directory and stores them in an S3 Vector bucket. **Now with automatic Terraform module detection and processing!**

## What's New

### Terraform Module Support

The system now automatically detects Terraform module references in your code and downloads them for embedding generation:

```terraform
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 3.0"
}
```

When detected, the system will:
- Download the module source code
- Extract all `.tf` files
- Generate embeddings for the module content
- Store them alongside your primary code embeddings

**Supported Sources**:
- Terraform Registry: `terraform-aws-modules/vpc/aws`
- Git repositories: `git::https://github.com/user/repo.git?ref=v1.0.0`
- Git with subdirectories: `git::https://github.com/user/repo.git//subdir`

### PocketFlow Architecture

The script has been refactored using [PocketFlow](https://github.com/The-Pocket/PocketFlow) for better:
- **Modularity**: Each processing step is a separate node
- **Error Handling**: Built-in retry mechanism with exponential backoff
- **Flexibility**: Easy to modify the workflow
- **Maintainability**: Clear data contracts between components

## Architecture

### Processing Flow

```
DiscoverFiles → FilterFiles → ReadFiles → ChunkFiles
                                              ↓
                                    DetectTerraformModules
                                              ↓
                        (if modules found) DownloadModules
                                              ↓
                                    ProcessModuleFiles
                                              ↓
                                    ChunkModuleFiles
                                              ↓
                                    GenerateEmbeddings → StoreVectors → Summary
```

## Prerequisites

This script uses dependencies from the parent project's `pyproject.toml`.

**Additional Requirement**: This implementation requires [PocketFlow](https://github.com/The-Pocket/PocketFlow) to be available at `/Users/patrick.heard/dev/util/PocketFlow`. You can either:
- Clone PocketFlow to that location, or
- Update the path in `nodes.py` and `flow.py`

## Configuration

### Required Environment Variables

Create a `.env` by copying `.env.example` and filling in your values:

- `AZURE_OPENAI_ENDPOINT` - Azure OpenAI endpoint URL
- `AZURE_OPENAI_API_KEY` - Azure OpenAI API key
- `AZURE_OPENAI_API_VERSION` - API version (e.g., "2023-05-15")
- `AZURE_OPENAI_EMBEDDINGS_MODEL` - Model name for embeddings
- `S3_VECTOR_BUCKET_NAME` - S3 Vector bucket name
- `S3_VECTOR_INDEX_NAME` - S3 Vector index name
- `S3_VECTOR_REGION` - AWS region for S3

### Optional Environment Variables

- `CHUNK_SIZE` - Maximum chunk size in characters (default: 1024)
- `CHUNK_OVERLAP` - Overlap between chunks (default: 100)
- `LOG_LEVEL` - Logging level: DEBUG, INFO, WARNING, ERROR (default: INFO)
- `INPUT_FOLDER` - Alternative to --input-folder argument


## Usage

### Basic Usage

Process all files in a directory:

```bash
uv run python scripts/generate_embeddings/main.py --input-folder /path/to/documents
```

### Dry Run (No S3 Uploads)

Test the processing without uploading:

```bash
uv run python scripts/generate_embeddings/main.py \
  --input-folder /path/to/documents \
  --dry-run
```

### Limit Files for Testing

Process only the first 10 files:

```bash
uv run python scripts/generate_embeddings/main.py \
  --input-folder /path/to/documents \
  --max-files 10
```

### Filter Files

Process only Python files:

```bash
uv run python scripts/generate_embeddings/main.py \
  --input-folder /path/to/documents \
  --include "*.py"
```

Exclude log files:

```bash
uv run python scripts/generate_embeddings/main.py \
  --input-folder /path/to/documents \
  --exclude "*.log"
```

### Combined Example

```bash
uv run python scripts/generate_embeddings/main.py \
  --input-folder /path/to/documents \
  --include "*.{py,md,txt}" \
  --exclude "**/node_modules/**" \
  --max-files 50 \
  --dry-run
```

## Command-Line Options

| Option | Description |
|--------|-------------|
| `--input-folder` | Path to the directory to process (required, or set INPUT_FOLDER env var) |
| `--dry-run` | Process files but skip S3 uploads |
| `--max-files N` | Process only the first N files (useful for testing) |
| `--include PATTERN` | Glob pattern to include files (e.g., `*.py`) |
| `--exclude PATTERN` | Glob pattern to exclude files (e.g., `*.log`) |

## Example Output

```
2024-10-06 12:00:00 - root - INFO - Starting embedding generation
2024-10-06 12:00:00 - root - INFO - Input folder: /path/to/code
2024-10-06 12:00:01 - root - INFO - Discovered 150 files
2024-10-06 12:00:01 - root - INFO - Filtered to 120 files for processing
2024-10-06 12:00:05 - root - INFO - Created 450 total chunks
2024-10-06 12:00:06 - root - INFO - Detected 3 unique Terraform modules
2024-10-06 12:00:08 - root - INFO - Downloaded 3 modules
2024-10-06 12:00:09 - root - INFO - Created 87 chunks from module files
2024-10-06 12:00:45 - root - INFO - Generated 537 embeddings (0 failures)
2024-10-06 12:00:50 - root - INFO - Stored 537 vectors (0 failures)
2024-10-06 12:00:50 - root - INFO - 
================================================================================
PROCESSING SUMMARY
================================================================================
Files discovered:        150
Files processed:         120
Files skipped:           30
Chunks created:          537
Vectors uploaded:        537
TF modules detected:     3
TF modules downloaded:   3
Failures:                0
================================================================================
```

## How It Works

### Nodes (nodes.py)

Individual processing units that each handle one specific task:

- **DiscoverFilesNode**: Recursively finds all files in input directory
- **FilterFilesNode**: Applies include/exclude patterns, skips binaries
- **ReadFilesNode**: Reads file contents
- **ChunkFilesNode**: Splits files into manageable chunks
- **DetectTerraformModulesNode**: Scans chunks for `module "name"` declarations
- **DownloadModulesNode**: Downloads detected modules from their sources
- **ProcessModuleFilesNode**: Reads `.tf` files from downloaded modules
- **ChunkModuleFilesNode**: Chunks module content
- **GenerateEmbeddingsNode**: Creates embeddings with automatic retry
- **StoreVectorsNode**: Uploads vectors to S3 with metadata
- **PrintSummaryNode**: Displays processing statistics

### Flows (flow.py)

Orchestrates nodes into a coherent workflow:

- **Main Flow**: Coordinates the entire embedding generation process
- **Module Processing Flow**: Handles Terraform module downloading and processing

### Shared Store

All nodes communicate via a shared dictionary that contains:
- Configuration and clients
- Discovered and filtered files
- Text chunks and embeddings
- Detected and downloaded modules
- Processing statistics

See `utils/data_schema.py` for complete documentation.
