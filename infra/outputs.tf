output "vpc_id" {
  description = "ID of the VPC."
  value       = module.network.vpc_id
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
  value       = "aws eks update-kubeconfig --region ${var.region} --profile ${var.aws_profile} --name ${module.eks.cluster_name}"
}
