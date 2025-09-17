# Core
- Be concise in all responses.
- Do not use adjectives or expresive language.
- Provide a brief summary then the task is complete.
- Challenge requested changes if there is a better way to accomplish the task.

# Code
## Python
- Dependency management is done with `uv`.
- This is a Python 3.13 project using FastAPI.
- Add type hints to all code.
- Format the code with `make fmt` after each change.
- Check for lint errors with `make lint` and fix any issues with generated code.

## Terraform
- Terraform and Terragrunt are used to manage AWS infrastructure.
- Terraform is in the `terraform/aws` directory.
- Terragrunt environment configuration is in `terraform/env` directory.

# Security
- Protect against the OWASP Top 10 web application vulnerabilities.