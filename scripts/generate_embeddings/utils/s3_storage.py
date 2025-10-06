#!/usr/bin/env python3
"""
S3 Vectors storage utility.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def store_vector(
    s3_client: Any,
    bucket_name: str,
    index_name: str,
    vector_id: str,
    vector: list[float],
    metadata: dict[str, Any],
    dry_run: bool = False,
) -> bool:
    """Store vector in S3 Vector bucket.

    Args:
        s3_client: boto3 S3 Vectors client
        bucket_name: S3 bucket name
        index_name: S3 index name
        vector_id: Unique identifier for the vector
        vector: Embedding vector
        metadata: Metadata dictionary
        dry_run: If True, skip actual upload

    Returns:
        True if successful, False otherwise
    """
    if dry_run:
        logger.info(f"[DRY RUN] Would upload vector {vector_id}")
        return True

    try:
        s3_client.put_vectors(
            vectorBucketName=bucket_name,
            indexName=index_name,
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


if __name__ == "__main__":
    import os
    import boto3
    from dotenv import load_dotenv

    load_dotenv()

    # Test the function (dry run)
    s3_client = boto3.client("s3vectors", region_name=os.getenv("S3_VECTOR_REGION"))

    test_vector = [0.1, 0.2, 0.3] * 100  # Mock 300-dim vector
    test_metadata = {
        "file_path": "/test/path.txt",
        "chunk_index": 0,
        "type": "test",
    }

    result = store_vector(
        s3_client,
        os.getenv("S3_VECTOR_BUCKET_NAME"),
        os.getenv("S3_VECTOR_INDEX_NAME"),
        "test_vector_id",
        test_vector,
        test_metadata,
        dry_run=True,
    )

    print(f"Store result: {result}")
