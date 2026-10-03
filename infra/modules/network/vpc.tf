module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 6.7"

  name = var.name
  cidr = var.vpc_cidr

  azs             = local.availability_zones
  private_subnets = local.private_subnet_cidrs
  public_subnets  = local.public_subnet_cidrs

  # Public mode: nodes get their own public IPs and reach the internet through the free Internet Gateway.
  # Private mode: one shared NAT gateway, which costs per hour and per GB of downloaded images.
  map_public_ip_on_launch = local.nodes_in_public_subnets
  enable_nat_gateway      = !local.nodes_in_public_subnets
  single_nat_gateway      = true

  # "kubernetes.io/role/*" lets the AWS Load Balancer Controller discover subnets.
  public_subnet_tags = merge(
    { "kubernetes.io/role/elb" = 1 },
    local.nodes_in_public_subnets ? local.node_subnet_tag : {},
  )
  private_subnet_tags = merge(
    { "kubernetes.io/role/internal-elb" = 1 },
    local.nodes_in_public_subnets ? {} : local.node_subnet_tag,
  )
}
