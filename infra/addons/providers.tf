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

provider "helm" {
  kubernetes = {
    host                   = data.aws_eks_cluster.this.endpoint
    cluster_ca_certificate = base64decode(data.aws_eks_cluster.this.certificate_authority[0].data)

    # Fresh token on every run, so it never expires mid-apply.
    exec = {
      api_version = "client.authentication.k8s.io/v1beta1"
      command     = "aws"
      args        = ["eks", "get-token", "--cluster-name", var.cluster_name, "--region", "eu-west-1", "--profile", "<aws-profile>"]
    }
  }
}
