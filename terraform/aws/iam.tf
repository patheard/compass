data "aws_iam_policy_document" "config" {
  statement {
    sid    = "ConfigAssumeRole"
    effect = "Allow"
    actions = [
      "sts:AssumeRole"
    ]
    resources = [
      "arn:aws:iam::*:role/compass-aws-config-job"
    ]
  }

  statement {
    sid    = "ConfigRead"
    effect = "Allow"
    actions = [
      "config:DescribeConfigRules",
      "config:DescribeComplianceByConfigRule"
    ]
    resources = [
      "*"
    ]
  }
}

data "aws_iam_policy_document" "dynamodb" {
  statement {
    sid    = "DynamoDBReadWrite"
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

data "aws_iam_policy_document" "sqs" {
  statement {
    sid    = "SQSReadWrite"
    effect = "Allow"
    actions = [
      "sqs:SendMessage",
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes"
    ]
    resources = aws_sqs_queue.compass_jobs.arn
  }
}
