module "compass" {
  source    = "github.com/cds-snc/terraform-modules//lambda?ref=v10.8.0"
  name      = var.product_name
  ecr_arn   = aws_ecr_repository.compass.arn
  image_uri = "${aws_ecr_repository.compass.repository_url}:latest"

  architectures          = ["arm64"]
  memory                 = 2048
  timeout                = 10
  enable_lambda_insights = true

  environment_variables = {
    GOOGLE_CLIENT_ID     = var.google_oauth_client_id
    GOOGLE_CLIENT_SECRET = var.google_oauth_client_secret
    SECRET_KEY           = var.secret_key
    BASE_URL             = "https://${var.domain}"
  }

  policies = [
    data.aws_iam_policy_document.dynamodb.json,
  ]

  billing_tag_value = var.billing_code
}

resource "aws_lambda_function_url" "compass" {
  function_name      = module.compass.function_name
  authorization_type = "NONE"
}

data "aws_iam_policy_document" "dynamodb" {
  statement {
    effect = "Allow"
    actions = [
      "dynamodb:CreateTable",
      "dynamodb:DescribeTable",
      "dynamodb:ListTables",
      "dynamodb:DeleteTable",
      "dynamodb:UpdateTable",
      "dynamodb:PutItem",
      "dynamodb:GetItem",
      "dynamodb:UpdateItem",
      "dynamodb:DeleteItem",
      "dynamodb:Query",
      "dynamodb:Scan",
      "dynamodb:BatchGetItem",
      "dynamodb:BatchWriteItem"
    ]
    resources = [
      "arn:aws:dynamodb:${var.region}:${var.account_id}:table/compass-*"
    ]
  }
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