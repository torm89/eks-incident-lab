variable "name" {
  description = "Name of the VPC and prefix for its resources."
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block of the VPC."
  type        = string
}

variable "availability_zone_count" {
  description = "Number of availability zones to spread subnets across. EKS requires at least 2."
  type        = number

  validation {
    condition     = var.availability_zone_count >= 2
    error_message = "EKS requires subnets in at least 2 availability zones."
  }
}

variable "node_subnet_type" {
  description = "Where worker nodes run: \"public\" (own public IPs, no NAT gateway) or \"private\" (behind a NAT gateway)."
  type        = string

  validation {
    condition     = contains(["public", "private"], var.node_subnet_type)
    error_message = "node_subnet_type must be \"public\" or \"private\"."
  }
}
