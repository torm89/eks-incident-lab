# The cluster is managed by the infra/ root module and looked up by name.
data "aws_eks_cluster" "this" {
  name = var.cluster_name
}
