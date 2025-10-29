"""Unit tests for S3 and SQS services."""

from unittest.mock import MagicMock, patch


from app.evidence.services import S3Service, SQSService


class TestS3Service:
    """Tests for S3Service class."""

    @patch.dict("os.environ", {"S3_EVIDENCE_BUCKET_NAME": "test-bucket"})
    def test_s3_service_initialization(self) -> None:
        """Test S3Service initialization."""
        service = S3Service()

        assert service.bucket_name == "test-bucket"
        assert service.region == "ca-central-1"

    @patch.dict("os.environ", {"S3_EVIDENCE_BUCKET_NAME": "test-bucket"})
    @patch("app.evidence.services.boto3.Session")
    def test_s3_client_creation(self, mock_session: MagicMock) -> None:
        """Test S3 client is created."""
        mock_boto_session = MagicMock()
        mock_session.return_value = mock_boto_session

        S3Service()

        mock_boto_session.client.assert_called_once_with(
            "s3", region_name="ca-central-1"
        )


class TestSQSService:
    """Tests for SQSService class."""

    @patch.dict("os.environ", {"SQS_QUEUE_URL": "https://sqs.test.com/queue"})
    def test_sqs_service_initialization(self) -> None:
        """Test SQSService initialization."""
        service = SQSService()

        assert service.queue_url == "https://sqs.test.com/queue"
        assert service.region == "ca-central-1"

    @patch.dict("os.environ", {"SQS_QUEUE_URL": "https://sqs.test.com/queue"})
    @patch("app.evidence.services.boto3.Session")
    def test_sqs_client_creation(self, mock_session: MagicMock) -> None:
        """Test SQS client is created."""
        mock_boto_session = MagicMock()
        mock_session.return_value = mock_boto_session

        SQSService()

        mock_boto_session.client.assert_called_once_with(
            "sqs", region_name="ca-central-1"
        )

    @patch.dict("os.environ", {"SQS_QUEUE_URL": "https://sqs.test.com/queue"})
    @patch("app.evidence.services.boto3.Session")
    def test_send_evidence_processing_message(self, mock_session: MagicMock) -> None:
        """Test sending evidence processing message to SQS."""
        mock_sqs = MagicMock()
        mock_sqs.send_message.return_value = {"MessageId": "msg-123"}
        mock_boto_session = MagicMock()
        mock_boto_session.client.return_value = mock_sqs
        mock_session.return_value = mock_boto_session

        service = SQSService()
        message_id = service.send_evidence_processing_message(
            control_id="control-123", evidence_id="evidence-123"
        )

        assert message_id == "msg-123"
        mock_sqs.send_message.assert_called_once()

    @patch.dict("os.environ", {"SQS_QUEUE_URL": ""})
    def test_send_message_without_queue_url(self) -> None:
        """Test sending message without queue URL returns None."""
        service = SQSService()

        result = service.send_evidence_processing_message(
            control_id="control-123", evidence_id="evidence-123"
        )

        assert result is None

    @patch.dict("os.environ", {"SQS_QUEUE_URL": "https://sqs.test.com/queue"})
    @patch("app.evidence.services.boto3.Session")
    def test_send_message_handles_errors(self, mock_session: MagicMock) -> None:
        """Test sending message handles SQS errors."""
        mock_sqs = MagicMock()
        mock_sqs.send_message.side_effect = Exception("SQS Error")
        mock_boto_session = MagicMock()
        mock_boto_session.client.return_value = mock_sqs
        mock_session.return_value = mock_boto_session

        service = SQSService()
        result = service.send_evidence_processing_message(
            control_id="control-123", evidence_id="evidence-123"
        )

        assert result is None
