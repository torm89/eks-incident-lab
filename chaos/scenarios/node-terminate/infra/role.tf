module "fis_role" {
  source = "../../../modules/fis-role"

  name                 = "${var.cluster_name}-fis-node-terminate"
  managed_policy_names = ["AWSFaultInjectionSimulatorEKSAccess"]
}
