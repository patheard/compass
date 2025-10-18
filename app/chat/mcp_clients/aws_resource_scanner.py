"""AWS resource scanner MCP client for identifying resources in Terraform files."""

from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict, List, Optional, Set

import boto3

from app.chat.mcp_clients.base import BaseMCPClient, MCPContext
from app.constants import AWS_RESOURCES

logger = logging.getLogger(__name__)


class AWSResourceScannerClient(BaseMCPClient):
    """MCP client for scanning AWS resources from Terraform files in S3 vectors."""

    RESOURCE_PATTERN = re.compile(r'resource\s+"(aws_[^"]+)"')

    def __init__(self, enabled: bool = True) -> None:
        """Initialize AWS resource scanner client."""
        super().__init__(enabled)
        self.s3_vector_bucket = os.environ.get("S3_VECTOR_BUCKET_NAME")
        self.s3_vector_index = os.environ.get("S3_VECTOR_INDEX_NAME")
        self.s3_vector_region = os.environ.get("S3_VECTOR_REGION")
        self.s3_vectors_client = boto3.client(
            "s3vectors", region_name=self.s3_vector_region
        )

    @property
    def name(self) -> str:
        """Return the name of this MCP client."""
        return "aws_resource_scanner"

    async def process(
        self, user_message: str, user_id: str, **kwargs: Any
    ) -> Optional[MCPContext]:
        """Process user message and return AWS resource context if requested.

        Only returns context if the user explicitly requests resource identification.
        This is determined by checking if 'identify_aws_resources' action is set.

        Args:
            user_message: The user's message text
            user_id: The user ID
            **kwargs: Additional context, including 'action' to check for explicit request

        Returns:
            MCPContext with identified AWS resources if requested, None otherwise
        """
        action = kwargs.get("action")

        # Only process if explicitly requested via action
        if action != "identify_aws_resources":
            return None

        try:
            resources = await self._identify_aws_resources()

            if not resources:
                return MCPContext(
                    content="No AWS resources found in Terraform files.",
                    metadata={"resource_count": 0, "resources": []},
                    client_name=self.name,
                )

            content = self._format_resource_list(resources)

            return MCPContext(
                content=content,
                metadata={
                    "resource_count": len(resources),
                    "resources": resources,
                },
                client_name=self.name,
            )

        except Exception as e:
            logger.exception(f"Error in AWS resource scanner: {e}")
            return None

    async def _identify_aws_resources(self) -> List[str]:
        """Identify AWS services from Terraform files in S3 vectors.

        Returns:
            List of AWS service names from the AWS_RESOURCES constant that match
            the resources found in Terraform files.
        """
        terraform_chunks = self._query_terraform_files()
        if not terraform_chunks:
            logger.info("No Terraform files found in S3 vectors")
            return []

        terraform_resources = self._extract_terraform_resources(terraform_chunks)
        matched_resources = self._match_aws_resources(terraform_resources)

        logger.info(
            f"Identified {len(matched_resources)} AWS resources from {len(terraform_chunks)} Terraform chunks"
        )
        return sorted(matched_resources)

    def _query_terraform_files(self) -> List[Dict[str, Any]]:
        """Query S3 vectors for all vectors with .tf file extension.

        Returns:
            List of vectors with Terraform file metadata.
        """
        try:
            vectors = []
            paginator = self.s3_vectors_client.get_paginator("list_vectors")
            page_iterator = paginator.paginate(
                vectorBucketName=self.s3_vector_bucket,
                indexName=self.s3_vector_index,
                returnMetadata=True,
            )

            for page in page_iterator:
                if "vectors" not in page:
                    continue

                for vector in page["vectors"]:
                    metadata = vector.get("metadata", {})
                    if metadata.get("file_extension") == ".tf":
                        vectors.append(vector)

            logger.info(f"Found {len(vectors)} Terraform file chunks in S3 vectors")
            return vectors

        except Exception as e:
            logger.exception(f"Error querying S3 vectors for Terraform files: {e}")
            return []

    def _extract_terraform_resources(self, vectors: List[Dict[str, Any]]) -> Set[str]:
        """Extract AWS resource names from Terraform file chunks.

        Args:
            vectors: List of S3 vectors containing Terraform file content

        Returns:
            Set of AWS resource names (e.g., 'aws_s3_bucket', 'aws_lambda_function')
        """
        resource_names: Set[str] = set()

        for vector in vectors:
            metadata = vector.get("metadata", {})
            chunk_text = metadata.get("chunk_text", "")

            # Find all resource declarations matching pattern: resource "aws_resource_name"
            matches = self.RESOURCE_PATTERN.findall(chunk_text)
            resource_names.update(matches)

        logger.info(f"Extracted {len(resource_names)} unique resource types")
        return resource_names

    def _match_aws_resources(self, terraform_resources: Set[str]) -> List[str]:
        """Match Terraform resource names against AWS_RESOURCES constant.

        Args:
            terraform_resources: Set of Terraform resource names (e.g., 'aws_s3_bucket')

        Returns:
            List of matching resource names from AWS_RESOURCES constant
        """
        matched: Set[str] = set()

        for tf_resource in terraform_resources:
            # Remove 'aws_' prefix from Terraform resource name
            if not tf_resource.startswith("aws_"):
                continue

            resource_base = tf_resource[4:]  # Remove 'aws_' prefix

            # Check if the resource base starts with any AWS_RESOURCES entry
            for aws_resource in AWS_RESOURCES:
                if resource_base.startswith(aws_resource):
                    matched.add(aws_resource)
                    break

        logger.info(f"Matched {len(matched)} resources against AWS_RESOURCES constant")
        return list(matched)

    def _format_resource_list(self, resources: List[str]) -> str:
        """Format the resource list for display.

        Args:
            resources: List of AWS resource names

        Returns:
            Formatted string of resources
        """
        resource_list = "\n".join(f"- {resource}" for resource in resources)
        return f"Identified {len(resources)} AWS resources:\n\n{resource_list}"
