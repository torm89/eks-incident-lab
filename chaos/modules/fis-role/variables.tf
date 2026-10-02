variable "name" {
  description = "Name of the IAM role that FIS assumes."
  type        = string
}

variable "managed_policy_names" {
  description = "AWS-managed FIS policies (service-role path) the role needs, e.g. AWSFaultInjectionSimulatorEC2Access."
  type        = list(string)
}
