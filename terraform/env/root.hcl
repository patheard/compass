locals {
  vars         = read_terragrunt_config("./env_vars.hcl")
  billing_code = "${local.vars.inputs.product_name}-${local.vars.inputs.env}"
}

inputs = {
  env          = local.vars.inputs.env
  product_name = local.vars.inputs.product_name
  region       = local.vars.inputs.region
  billing_code = local.billing_code
}

remote_state {
  backend = "s3"
  generate = {
    path      = "backend.tf"
    if_exists = "overwrite_terragrunt"
  }
  config = {
    encrypt             = true
    bucket              = "${local.billing_code}-tf"
    use_lockfile        = true
    region              = local.vars.inputs.region
    key                 = "terraform.tfstate"
    s3_bucket_tags      = { CostCentre : local.billing_code }
  }
}

generate "provider" {
  path      = "provider.tf"
  if_exists = "overwrite"
  contents  = file("./common/provider.tf")
}
