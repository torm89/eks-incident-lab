locals {
  availability_zones = slice(data.aws_availability_zones.available.names, 0, var.availability_zone_count)

  private_subnet_cidrs = [for index, _ in local.availability_zones : cidrsubnet(var.vpc_cidr, 4, index)]
  public_subnet_cidrs  = [for index, _ in local.availability_zones : cidrsubnet(var.vpc_cidr, 8, index + 48)]

  nodes_in_public_subnets = var.node_subnet_type == "public"

  # Marks the subnets that host worker nodes, e.g. for AWS FIS targets in chaos/.
  node_subnet_tag = { NodeSubnet = "true" }
}
