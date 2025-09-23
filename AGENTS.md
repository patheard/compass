# Core
- Be concise in all responses.
- Do not use adjectives or expresive language.
- Provide a brief summary when the task is complete.

# Code
## Python
- Dependency management is done with `uv`.
- This is a Python 3.13 project using FastAPI.
- Add type hints to all code.
- When making frontend page changes follow the examples in the `./app/templates` directory.
- Before completing a task, run `make fmt`, `make lint` and `make security` and fix any issues found before considering the task finished.

## Terraform
- Terraform and Terragrunt are used to manage AWS infrastructure.
- Terraform is in the `terraform/aws` directory.
- Terragrunt environment configuration is in `terraform/env` directory.

# Security
- Protect against the OWASP Top 10 web application vulnerabilities.