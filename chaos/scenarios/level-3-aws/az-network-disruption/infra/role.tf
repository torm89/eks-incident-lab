module "fis_role" {
  source = "../../../../modules/fis-role"

  name                 = "${var.cluster_name}-fis-az-network-disruption"
  managed_policy_names = ["AWSFaultInjectionSimulatorNetworkAccess"]
}
