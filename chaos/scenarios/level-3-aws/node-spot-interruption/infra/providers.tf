# Credentials: the AWS_PROFILE environment variable (see README, "Local setup").
provider "aws" {
  region = "eu-west-1"

  default_tags {
    tags = {
      Project   = "eks-incident-lab"
      ManagedBy = "terraform"
    }
  }
}
