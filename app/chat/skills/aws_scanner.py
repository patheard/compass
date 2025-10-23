"""Skill for scanning AWS resources from Terraform files."""

import logging
import os
import re
from typing import Any, Dict, List, Optional, Set

import boto3

from app.assessments.validation import AssessmentRequest
from app.chat.skills.base import Action, AgentSkill, SkillContext, SkillResult
from app.constants import AWS_RESOURCES

logger = logging.getLogger(__name__)


class AWSResourceScannerSkill(AgentSkill):
    """Skill for scanning Terraform files to identify AWS services."""

    name = "aws_scanner"
    description = "Scan Terraform files to identify AWS services"
    action_types = ["identify_aws_resources"]

    # Terraform resource pattern
    RESOURCE_PATTERN = re.compile(r'resource\s+"(aws_[^"]+)"')

    def __init__(self) -> None:
        """Initialize AWS resource scanner skill."""
        self.s3_vector_bucket = os.environ.get("S3_VECTOR_BUCKET_NAME")
        self.s3_vector_index = os.environ.get("S3_VECTOR_INDEX_NAME")
        self.s3_vector_region = os.environ.get("S3_VECTOR_REGION")
        self.s3_vectors_client = boto3.client(
            "s3vectors", region_name=self.s3_vector_region
        )

    async def can_execute(
        self, action_type: str, params: Dict[str, Any], context: SkillContext
    ) -> bool:
        """Check if this skill can handle the action."""
        return action_type == "identify_aws_resources"

    async def execute(
        self, action_type: str, params: Dict[str, Any], context: SkillContext
    ) -> SkillResult:
        """Execute the AWS resource scanning."""
        assessment_id = params.get("assessment_id")
        if not assessment_id:
            return SkillResult(success=False, message="Missing assessment_id")

        try:
            # Identify AWS resources from Terraform files
            aws_resources = await self._identify_aws_resources()

            # Update assessment with discovered resources
            if aws_resources:
                assessment = context.assessment_service.get_assessment(
                    assessment_id, context.user_id
                )

                if not assessment:
                    return SkillResult(success=False, message="Assessment not found")

                update_data = AssessmentRequest(
                    product_name=assessment.product_name,
                    product_description=assessment.product_description,
                    status=assessment.status,
                    aws_account_id=assessment.aws_account_id,
                    github_repo_controls=assessment.github_repo_controls,
                    aws_resources=aws_resources,
                )

                context.assessment_service.update_assessment(
                    assessment_id, context.user_id, update_data
                )

            return SkillResult(
                success=True,
                message=f"Identified {len(aws_resources)} AWS services",
                data={
                    "assessment_id": assessment_id,
                    "aws_resources": aws_resources,
                },
                reload_page=True,
            )

        except Exception as e:
            logger.exception(f"Error scanning AWS resources: {e}")
            return SkillResult(success=False, message="Failed to scan AWS resources")

    async def get_available_actions(self, context: SkillContext) -> List[Action]:
        """Return scan action if on assessment page with AWS account."""
        actions: List[Action] = []

        # Check if on assessment page
        assessment_match = re.search(
            r"/assessments/([a-f0-9-]+)$",
            context.current_url or "",
        )

        if assessment_match:
            assessment_id = assessment_match.group(1)
            try:
                assessment = context.assessment_service.get_assessment(
                    assessment_id, context.user_id
                )

                if assessment and assessment.aws_account_id:
                    actions.append(
                        Action(
                            action_type="identify_aws_resources",
                            label="Identify AWS services",
                            description="Scan Terraform files to identify AWS services",
                            params={"assessment_id": assessment_id},
                        )
                    )
            except Exception as e:
                logger.exception(f"Error checking assessment for AWS scanner: {e}")

        return actions

    async def get_context_description(
        self, actions: List[Action], context: SkillContext
    ) -> Optional[str]:
        """Return context description for AWS scanner capability."""
        if actions:
            return "- **Identify AWS services** by scanning Terraform files"
        return None

    async def _identify_aws_resources(self) -> List[str]:
        """Identify AWS services from Terraform files in S3 vectors.

        Returns:
            List of AWS service names that match the resources found in Terraform files.
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
