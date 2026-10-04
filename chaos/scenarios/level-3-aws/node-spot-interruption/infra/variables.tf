variable "cluster_name" {
  description = "Name of the EKS cluster created by infra/."
  type        = string
  default     = "eks-incident-lab"
}

variable "interruption_notice" {
  description = "Time between the spot interruption notice and the node being stopped (ISO 8601)."
  type        = string
  default     = "PT2M"
}
