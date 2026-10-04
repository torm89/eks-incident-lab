variable "cluster_name" {
  description = "Name of the EKS cluster created by infra/."
  type        = string
  default     = "eks-incident-lab"
}

variable "availability_zone" {
  description = "Availability zone whose worker node subnets lose network connectivity."
  type        = string
  default     = "eu-west-1a"
}

variable "duration" {
  description = "How long the availability zone stays cut off (ISO 8601)."
  type        = string
  default     = "PT5M"
}
