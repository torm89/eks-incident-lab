variable "cluster_name" {
  description = "Name of the EKS cluster."
  type        = string
}

variable "kubernetes_version" {
  description = "Kubernetes version of the EKS control plane."
  type        = string
}

variable "vpc_id" {
  description = "ID of the VPC the cluster runs in."
  type        = string
}

variable "subnet_ids" {
  description = "IDs of the private subnets for the control plane and worker nodes."
  type        = list(string)

  validation {
    condition     = length(var.subnet_ids) >= 2
    error_message = "EKS requires at least 2 subnets."
  }
}

variable "node_instance_types" {
  description = "EC2 instance types for worker nodes."
  type        = list(string)
}

variable "node_capacity_type" {
  description = "Capacity type of worker nodes: ON_DEMAND or SPOT."
  type        = string

  validation {
    condition     = contains(["ON_DEMAND", "SPOT"], var.node_capacity_type)
    error_message = "node_capacity_type must be ON_DEMAND or SPOT."
  }
}

variable "node_count" {
  description = "Minimum, desired and maximum number of worker nodes."
  type = object({
    min     = number
    desired = number
    max     = number
  })
}

variable "api_allowed_cidrs" {
  description = "CIDR blocks allowed to reach the public Kubernetes API endpoint."
  type        = list(string)
}
