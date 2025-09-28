output "compass_url" {
  description = "The URL of the Compass Lambda function"
  value       = aws_lambda_function_url.compass.function_url
}