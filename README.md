# Compass :compass:

A platform that will provide automated security assessment tools. For now it does next to nothing since it's very much a work in progress.

## Local

Add your secrets to a `.env` file.

```sh
cp .env.example .env
make run
```

## Automated evidence

You can add AWS Config automated evidence collection jobs using the `/job-templates/new` endpoint. The config structure is below with the `prefix` matching the beginning of the Config rule name you want to check:

```json
{
  "rules": [
    {
      "link": "https://docs.aws.amazon.com/config/latest/developerguide/acm-certificate-expiration-check.html",
      "prefix": "securityhub-acm-certificate-expiration-check"
    },
    {
      "link": "https://docs.aws.amazon.com/config/latest/developerguide/acm-certificate-rsa-check.html",
      "prefix": "securityhub-acm-certificate-rsa-check"
    },
    {
      "link": "https://docs.aws.amazon.com/config/latest/developerguide/alb-http-to-https-redirection-check.html",
      "prefix": "securityhub-alb-http-to-https-redirection-check"
    },
    {
      "link": "https://docs.aws.amazon.com/config/latest/developerguide/elbv2-listener-encryption-in-transit.html",
      "prefix": "securityhub-elbv2-listener-encryption-in-transit"
    },
    {
      "link": "https://docs.aws.amazon.com/config/latest/developerguide/elbv2-predefined-security-policy-ssl-check.html",
      "prefix": "securityhub-elbv2-predefined-security-policy-ssl-check"
    }
  ]
}
```

The AWS account you are checking needs an IAM role named `compass-aws-config-job` with the following trust policy and the ability to list/describe AWS Config rules:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "CompassAssume",
            "Effect": "Allow",
            "Principal": {
                "AWS": "arn:aws:iam::AWS_ACCOUNT_ID:role/compass-job-processor"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
```

## Chat and Retrieval Augmented Generation

The project is setup to use Azure OpenAI models for chat completions and embeddings:

1. Create an [S3 Vector bucket and index](https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-vectors-getting-started.html) (no Terraform support yet).
1. Use `./scripts/generate_embeddings.py` to generate and store the vector embeddings.
1. These embeddings will be automatically used by the chat.


## Google OAuth
Your Google OAuth 2.0 client ID should be setup like so:
- `Authorized JavaScript origins`: http://localhost:8000
- `Authorized redirect URIs`: http://localhost:8000/auth/callback
