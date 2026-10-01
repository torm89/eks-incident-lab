data "aws_availability_zones" "available" {
  # Skip Local Zones, which do not support EKS.
  filter {
    name   = "opt-in-status"
    values = ["opt-in-not-required"]
  }
}
