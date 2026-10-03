module "network" {
  source = "./modules/network"

  name                    = var.environment_name
  vpc_cidr                = var.vpc_cidr
  availability_zone_count = var.availability_zone_count
  node_subnet_type        = var.node_subnet_type
}

module "eks" {
  source = "./modules/eks"

  cluster_name       = var.environment_name
  kubernetes_version = var.kubernetes_version

  vpc_id                   = module.network.vpc_id
  node_subnet_ids          = module.network.node_subnet_ids
  control_plane_subnet_ids = module.network.private_subnet_ids

  node_instance_types = var.node_instance_types
  node_capacity_type  = var.node_capacity_type
  node_count          = var.node_count

  api_allowed_cidrs = var.api_allowed_cidrs
}

module "registry" {
  source = "./modules/registry"

  name_prefix      = var.environment_name
  repository_names = var.container_repositories
}
