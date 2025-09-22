"""SQS service for sending evidence processing messages."""

import json
import logging
import os
from typing import Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger(__name__)


class SQSService:
    """Service for sending SQS messages for evidence processing."""

    def __init__(self) -> None:
        """Initialize SQS service."""
        self.region = os.getenv("AWS_REGION", "ca-central-1")
        self.queue_url = os.getenv("SQS_QUEUE_URL")
        self.endpoint_url = os.getenv("SQS_ENDPOINT_URL")

        # Create SQS client
        session = boto3.Session()
        if self.endpoint_url:
            self.sqs_client = session.client(
                "sqs",
                region_name=self.region,
                endpoint_url=self.endpoint_url,
            )
        else:
            self.sqs_client = session.client("sqs", region_name=self.region)

    def send_evidence_processing_message(
        self, control_id: str, evidence_id: str
    ) -> Optional[str]:
        """
        Send a message to SQS for evidence processing.

        Args:
            control_id: The control ID
            evidence_id: The evidence ID

        Returns:
            Message ID if successful, None if failed
        """
        if not self.queue_url:
            logger.warning("SQS queue URL not configured, skipping message send")
            return None

        message_body = {
            "control_id": control_id,
            "evidence_id": evidence_id,
        }

        try:
            response = self.sqs_client.send_message(
                QueueUrl=self.queue_url,
                MessageBody=json.dumps(message_body),
            )

            message_id = response.get("MessageId")
            logger.info(
                f"Sent evidence processing message for evidence {evidence_id} "
                f"with message ID {message_id}"
            )
            return message_id

        except (BotoCoreError, ClientError) as e:
            logger.error(
                f"Failed to send evidence processing message for evidence {evidence_id}: {e}"
            )
            return None
        except Exception as e:
            logger.error(
                f"Unexpected error sending evidence processing message for evidence {evidence_id}: {e}"
            )
            return None
