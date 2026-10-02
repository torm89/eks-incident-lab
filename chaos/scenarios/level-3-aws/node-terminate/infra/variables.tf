variable "cluster_name" {
  description = "Name of the EKS cluster created by infra/."
  type        = string
  default     = "torm-eks"
}

variable "terminated_nodes_percentage" {
  description = "Percentage of node group instances terminated at once."
  type        = number
  default     = 50

  validation {
    condition     = var.terminated_nodes_percentage > 0 && var.terminated_nodes_percentage <= 100
    error_message = "terminated_nodes_percentage must be between 1 and 100."
  }
}
