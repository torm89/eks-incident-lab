# The template is free. You pay only while the experiment runs (about $0.10 per action-minute).
resource "aws_fis_experiment_template" "this" {
  description = "Terminate part of the EKS node group without warning"
  role_arn    = module.fis_role.arn

  stop_condition {
    source = "none"
  }

  action {
    name      = "terminate-nodes"
    action_id = "aws:eks:terminate-nodegroup-instances"

    target {
      key   = "Nodegroups"
      value = "cluster-node-groups"
    }

    parameter {
      key   = "instanceTerminationPercentage"
      value = tostring(var.terminated_nodes_percentage)
    }
  }

  # Found by tag at start time, so the template can exist before the cluster.
  # infra/ tags every resource with Project=torm-eks.
  target {
    name           = "cluster-node-groups"
    resource_type  = "aws:eks:nodegroup"
    selection_mode = "ALL"

    resource_tag {
      key   = "Project"
      value = "torm-eks"
    }
  }

  tags = {
    Name = "${var.cluster_name}-node-terminate"
  }
}
