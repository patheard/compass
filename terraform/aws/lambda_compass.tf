module "compass" {
  source    = "github.com/cds-snc/terraform-modules//lambda?ref=v10.8.0"
  name      = var.product_name
  ecr_arn   = aws_ecr_repository.compass.arn
  image_uri = "${aws_ecr_repository.compass.repository_url}:latest"

  architectures          = ["arm64"]
  memory                 = 2048
  timeout                = 60
  enable_lambda_insights = true

  environment_variables = {
    AZURE_OPENAI_API_KEY                = var.azure_openai_api_key
    AZURE_OPENAI_ENDPOINT               = var.azure_openai_endpoint
    AZURE_OPENAI_API_VERSION            = var.azure_openai_api_version
    AZURE_OPENAI_COMPLETIONS_MODEL_NAME = var.azure_openai_completions_model
    AZURE_OPENAI_EMBEDDINGS_MODEL_NAME  = var.azure_openai_embeddings_model
    GOOGLE_CLIENT_ID                    = var.google_oauth_client_id
    GOOGLE_CLIENT_SECRET                = var.google_oauth_client_secret
    S3_VECTOR_BUCKET_NAME               = var.s3_vector_bucket
    S3_VECTOR_INDEX_NAME                = var.s3_vector_index
    S3_VECTOR_REGION                    = var.s3_vector_region
    SECRET_KEY                          = var.secret_key
    BASE_URL                            = "https://${var.domain}"
    SQS_QUEUE_URL                       = aws_sqs_queue.compass_jobs.id
  }

  policies = [
    data.aws_iam_policy_document.dynamodb.json,
    data.aws_iam_policy_document.sqs.json
  ]

  billing_tag_value = var.billing_code
}

resource "aws_lambda_function_url" "compass" {
  function_name      = module.compass.function_name
  authorization_type = "NONE"
}

#
# Function warmer
#
resource "aws_cloudwatch_event_rule" "compass" {
  name                = "invoke-compass"
  description         = "Keep the function toasty warm"
  schedule_expression = "rate(5 minutes)"
}

resource "aws_cloudwatch_event_target" "compass" {
  target_id = "invoke-lambda"
  rule      = aws_cloudwatch_event_rule.compass.name
  arn       = module.compass.function_arn
  input     = jsonencode({})
}

resource "aws_lambda_permission" "compass" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = module.compass.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.compass.arn
}