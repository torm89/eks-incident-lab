variable "name_prefix" {
  description = "Prefix of every repository name, e.g. eks-incident-lab -> eks-incident-lab/<name>."
  type        = string
}

variable "repository_names" {
  description = "Names of the container image repositories, one per service in services/."
  type        = list(string)
}
