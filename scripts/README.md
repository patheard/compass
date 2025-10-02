# Generate Embeddings Script

A standalone Python script that uses Azure OpenAI to generate text embeddings for files in a directory and stores them in an S3 Vector bucket.

## Prerequisites

This script uses dependencies from the parent project's `pyproject.toml`:

## Configuration

### Required Environment Variables

Create a `.env` file in the project root or set these environment variables:

```bash
# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_KEY=your-api-key-here
AZURE_OPENAI_EMBEDDINGS_MODEL=text-embedding-3-small

# S3 Configuration
S3_VECTOR_BUCKET_NAME=your-vector-bucket-name

# Optional: AWS credentials (if not using default boto3 credentials)
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_DEFAULT_REGION=us-east-1
```

### Optional Environment Variables

```bash
# Text chunking (default: 2000 characters)
CHUNK_SIZE=2000
CHUNK_OVERLAP=200

# Logging level (default: INFO)
LOG_LEVEL=DEBUG
```

## Usage

### Basic Usage

Process all files in a directory:

```bash
uv run python scripts/generate_embeddings.py --input-folder /path/to/documents
```

### Filter Files

Process only Python files:

```bash
uv run python scripts/generate_embeddings.py \
  --input-folder /path/to/documents \
  --include "*.py"
```

Exclude log files:

```bash
uv run python scripts/generate_embeddings.py \
  --input-folder /path/to/documents \
  --exclude "*.log"
```

### Combined Example

```bash
uv run python scripts/generate_embeddings.py \
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
| `--max-files N` | Process only the first N files |
| `--include PATTERN` | Glob pattern to include files (e.g., `*.py`) |
| `--exclude PATTERN` | Glob pattern to exclude files (e.g., `*.log`) |
