module "evidence_bucket" {
  source            = "github.com/cds-snc/terraform-modules//S3?ref=v10.8.1"
  bucket_name       = "${var.product_name}-cds-evidence"
  billing_tag_value = var.billing_code

  lifecycle_rule = [
    local.lifecycle_transition_storage
  ]

  versioning = {
    enabled = true
  }
}

locals {
  # Transition objects to cheaper storage classes over time
  lifecycle_transition_storage = {
    id      = "transition_storage"
    enabled = true
    transition = [
      {
        days          = "90"
        storage_class = "STANDARD_IA"
      },
      {
        days          = "180"
        storage_class = "GLACIER"
      }
    ]
  }
}