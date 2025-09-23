resource "aws_sqs_queue" "compass_jobs" {
  name                       = "compass-jobs"
  delay_seconds              = 0
  max_message_size           = 2048
  message_retention_seconds  = 1209600 # 14 days
  receive_wait_time_seconds  = 0
  visibility_timeout_seconds = 60

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.compass_jobs_dlq.arn
    maxReceiveCount     = 3
  })

  tags = local.common_tags
}

# Dead letter queue
resource "aws_sqs_queue" "compass_jobs_dlq" {
  name = "compass-jobs-dlq"
  tags = local.common_tags
}
