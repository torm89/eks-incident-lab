variable "environment_name" {
  description = "Name of the environment. Used as the VPC and EKS cluster name."
  type        = string
  default     = "eks-incident-lab"
}

variable "vpc_cidr" {
  description = "CIDR block of the VPC."
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zone_count" {
  description = "Number of availability zones to spread subnets across. EKS requires at least 2."
  type        = number
  default     = 2
}

variable "node_subnet_type" {
  description = <<-EOT
    Where worker nodes run:
    "public"  - nodes have public IPs, no NAT gateway. Cheapest: image downloads are free.
    "private" - nodes are hidden behind a NAT gateway. Closer to production, but you pay for NAT hours and data.
    Inbound internet traffic to nodes is blocked by security groups in both modes.
  EOT
  type        = string
  default     = "public"

  validation {
    condition     = contains(["public", "private"], var.node_subnet_type)
    error_message = "node_subnet_type must be \"public\" or \"private\"."
  }
}

variable "kubernetes_version" {
  description = "Kubernetes version of the EKS control plane."
  type        = string
  default     = "1.36"
}

variable "node_instance_types" {
  description = "EC2 instance types for worker nodes. Several types improve spot availability."
  type        = list(string)
  default     = ["t3.medium", "t3a.medium"]
}

variable "node_capacity_type" {
  description = "Capacity type of worker nodes: ON_DEMAND or SPOT."
  type        = string
  default     = "SPOT"
}

variable "node_count" {
  description = <<-EOT
    Minimum, desired and maximum number of worker nodes.
    3 nodes: a t3.medium runs at most 17 pods, and the lab needs ~30, plus room to lose a node.
    "desired" only applies when the node group is created; later changes are ignored (scale with the AWS CLI).
  EOT
  type = object({
    min     = number
    desired = number
    max     = number
  })
  default = {
    min     = 2
    desired = 3
    max     = 4
  }
}

variable "api_allowed_cidrs" {
  description = "CIDR blocks allowed to reach the public Kubernetes API endpoint. Narrow this to your own IP."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "container_repositories" {
  description = "ECR repositories for our own services (see services/). Worker nodes can pull from them."
  type        = list(string)
  default     = ["ai-assistant", "llm-gateway"]
}
