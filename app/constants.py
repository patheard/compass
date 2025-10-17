"""Application-wide constants."""

ASSESSMENT_STATUSES = [
    "prepare",
    "categorize",
    "select",
    "implement",
    "assess",
    "authorize",
    "monitor",
]

# Common AWS resource types for assessment filtering
AWS_RESOURCES = [
    "acm",
    "api_gateway",
    "alb",
    "athena",
    "cloudfront",
    "cloudwatch",
    "db_proxy",
    "dynamodb",
    "ecs",
    "eks",
    "iam",
    "internet_gateway",
    "kms",
    "lambda",
    "nat_gateway",
    "network_acl",
    "rds",
    "route53",
    "s3",
    "secretsmanager",
    "security_group",
    "ses",
    "sns",
    "sqs",
    "ssm_parameter",
    "vpc",
    "waf",
]

# NIST 800-53 Revision 5 Control IDs
NIST_CONTROL_IDS = ["CP-10(2)", "SC-8", "SC-8(1)", "SC-23"]
