output "vpc_id" {
  description = "ID of the VPC."
  value       = module.network.vpc_id
}

output "region" {
  description = "AWS region of the environment."
  value       = data.aws_region.current.region
}

output "cluster_name" {
  description = "Name of the EKS cluster."
  value       = module.eks.cluster_name
}

output "cluster_endpoint" {
  description = "Endpoint of the Kubernetes API server."
  value       = module.eks.cluster_endpoint
}

output "configure_kubectl" {
  description = "Command that adds the cluster to your local kubeconfig."
  value       = "aws eks update-kubeconfig --region ${data.aws_region.current.region} --name ${module.eks.cluster_name}"
}

output "container_repository_urls" {
  description = "ECR repository URL per service. Push images with scripts/push_images.py."
  value       = module.registry.repository_urls
}
