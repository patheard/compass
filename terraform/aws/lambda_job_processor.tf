module "compass_job_processor" {
  source    = "github.com/cds-snc/terraform-modules//lambda?ref=v10.8.0"
  name      = "${var.product_name}-job-processor"
  ecr_arn   = aws_ecr_repository.compass_job_processor.arn
  image_uri = "${aws_ecr_repository.compass_job_processor.repository_url}:latest"

  architectures          = ["arm64"]
  memory                 = 1024
  timeout                = 60
  enable_lambda_insights = true

  policies = [
    data.aws_iam_policy_document.dynamodb.json,
    data.aws_iam_policy_document.sqs.json,
    data.aws_iam_policy_document.config.json,
  ]

  billing_tag_value = var.billing_code
}

#
# SQS trigger for Lambda
#
resource "aws_lambda_event_source_mapping" "compass_job_processor" {
  event_source_arn = aws_sqs_queue.compass_jobs.arn
  function_name    = module.compass_job_processor.function_arn
  batch_size       = 10

  function_response_types = ["ReportBatchItemFailures"]
}