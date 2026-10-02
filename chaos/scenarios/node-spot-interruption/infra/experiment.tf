# The template is free. You pay only while the experiment runs (about $0.10 per action-minute).
resource "aws_fis_experiment_template" "this" {
  description = "Send a spot interruption notice to one worker node"
  role_arn    = module.fis_role.arn

  stop_condition {
    source = "none"
  }

  action {
    name      = "interrupt-spot-node"
    action_id = "aws:ec2:send-spot-instance-interruptions"

    target {
      key   = "SpotInstances"
      value = "one-spot-node"
    }

    parameter {
      key   = "durationBeforeInterruption"
      value = var.interruption_notice
    }
  }

  # Found by tag at start time, so the template can exist before the cluster.
  target {
    name           = "one-spot-node"
    resource_type  = "aws:ec2:spot-instance"
    selection_mode = "COUNT(1)"

    resource_tag {
      key   = "eks:cluster-name"
      value = var.cluster_name
    }

    filter {
      path   = "State.Name"
      values = ["running"]
    }
  }

  tags = {
    Name = "${var.cluster_name}-node-spot-interruption"
  }
}
