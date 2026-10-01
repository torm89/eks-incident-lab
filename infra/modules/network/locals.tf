locals {
  availability_zones = slice(data.aws_availability_zones.available.names, 0, var.availability_zone_count)

  private_subnet_cidrs = [for index, _ in local.availability_zones : cidrsubnet(var.vpc_cidr, 4, index)]
  public_subnet_cidrs  = [for index, _ in local.availability_zones : cidrsubnet(var.vpc_cidr, 8, index + 48)]
}
