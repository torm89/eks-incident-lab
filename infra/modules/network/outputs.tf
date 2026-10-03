output "vpc_id" {
  description = "ID of the VPC."
  value       = module.vpc.vpc_id
}

output "private_subnet_ids" {
  description = "IDs of the private subnets."
  value       = module.vpc.private_subnets
}

output "public_subnet_ids" {
  description = "IDs of the public subnets."
  value       = module.vpc.public_subnets
}

output "node_subnet_ids" {
  description = "IDs of the subnets that host worker nodes (public or private, see node_subnet_type)."
  value       = local.nodes_in_public_subnets ? module.vpc.public_subnets : module.vpc.private_subnets
}
