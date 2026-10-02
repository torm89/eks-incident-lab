terraform {
  backend "s3" {
    bucket       = "<state-bucket>"
    key          = "chaos/terraform.tfstate"
    region       = "eu-west-1"
    profile      = "<aws-profile>"
    encrypt      = true
    use_lockfile = true
  }
}
