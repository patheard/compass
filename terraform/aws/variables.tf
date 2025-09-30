variable "account_id" {
  description = "AWS account ID."
  type        = string
}

variable "azure_openai_api_key" {
  description = "Azure OpenAI API key."
  type        = string
  sensitive   = true
}

variable "azure_openai_endpoint" {
  description = "Azure OpenAI endpoint URL."
  type        = string
  sensitive   = true
}

variable "azure_openai_api_version" {
  description = "Azure OpenAI API version."
  type        = string
}

variable "azure_openai_model" {
  description = "Azure OpenAI model to use (e.g. gpt-4, gpt-4o, gpt-4o-mini, gpt-35-turbo)."
  type        = string
}

variable "billing_code" {
  description = "Billing code tag value."
  type        = string
}

variable "domain" {
  description = "Base URL for Compass (e.g. compass.canada.ca)."
  type        = string
}

variable "env" {
  description = "Environment name (e.g. prod, staging)."
  type        = string
}

variable "google_oauth_client_id" {
  description = "Google OAuth Client ID."
  type        = string
  sensitive   = true
}

variable "google_oauth_client_secret" {
  description = "Google OAuth Client Secret."
  type        = string
  sensitive   = true
}

variable "product_name" {
  description = "The name of the product you are deploying."
  type        = string
}

variable "region" {
  description = "AWS region."
  type        = string
}

variable "secret_key" {
  description = "Session secret key."
  type        = string
  sensitive   = true
}
