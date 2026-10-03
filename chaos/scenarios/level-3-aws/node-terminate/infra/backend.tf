terraform {
  # The bucket comes from backend.hcl in the repo root (see README, "Local setup").
  backend "s3" {
    key          = "chaos/node-terminate/terraform.tfstate"
    region       = "eu-west-1"
    encrypt      = true
    use_lockfile = true
  }
}
