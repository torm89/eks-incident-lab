module "fis_role" {
  source = "../../../../modules/fis-role"

  name                 = "${var.cluster_name}-fis-node-spot-interruption"
  managed_policy_names = ["AWSFaultInjectionSimulatorEC2Access"]
}
