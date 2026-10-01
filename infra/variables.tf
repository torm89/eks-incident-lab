variable "environment_name" {
  description = "Name of the environment. Used as the VPC and EKS cluster name."
  type        = string
  default     = "torm-eks"
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
  description = "Minimum, desired and maximum number of worker nodes."
  type = object({
    min     = number
    desired = number
    max     = number
  })
  default = {
    min     = 1
    desired = 2
    max     = 3
  }
}

variable "api_allowed_cidrs" {
  description = "CIDR blocks allowed to reach the public Kubernetes API endpoint. Narrow this to your own IP."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}
