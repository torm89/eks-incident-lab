variable "name_prefix" {
  description = "Prefix of every repository name, e.g. torm-eks -> torm-eks/<name>."
  type        = string
}

variable "repository_names" {
  description = "Names of the container image repositories, one per service in services/."
  type        = list(string)
}
