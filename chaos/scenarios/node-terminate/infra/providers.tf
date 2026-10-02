provider "aws" {
  region  = "eu-west-1"
  profile = "<aws-profile>"

  default_tags {
    tags = {
      Project   = "torm-eks"
      ManagedBy = "terraform"
    }
  }
}
