terraform {
  required_version = ">= 1.10.0" # use_lockfile in the S3 backend

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.59"
    }
  }
}
