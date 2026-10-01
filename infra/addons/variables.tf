variable "cluster_name" {
  description = "Name of the EKS cluster created by the infra/ root module."
  type        = string
  default     = "torm-eks"
}
