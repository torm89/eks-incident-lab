# FIS experiment templates are free. You pay only while an experiment runs
# (about $0.10 per action-minute). Start one with the commands in outputs.tf.

resource "aws_fis_experiment_template" "node_spot_interruption" {
  description = "Send a spot interruption notice to one worker node"
  role_arn    = aws_iam_role.fis.arn

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
      value = var.spot_interruption_notice
    }
  }

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

resource "aws_fis_experiment_template" "node_terminate" {
  description = "Terminate half of the worker nodes in the EKS node group"
  role_arn    = aws_iam_role.fis.arn

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
      value = "50"
    }
  }

  target {
    name           = "cluster-node-groups"
    resource_type  = "aws:eks:nodegroup"
    selection_mode = "ALL"

    resource_tag {
      key   = local.project_tag.key
      value = local.project_tag.value
    }
  }

  tags = {
    Name = "${var.cluster_name}-node-terminate"
  }
}

resource "aws_fis_experiment_template" "az_network_disruption" {
  description = "Cut all network traffic of the private subnets in one availability zone"
  role_arn    = aws_iam_role.fis.arn

  stop_condition {
    source = "none"
  }

  action {
    name      = "disrupt-az"
    action_id = "aws:network:disrupt-connectivity"

    target {
      key   = "Subnets"
      value = "private-subnets-in-az"
    }

    parameter {
      key   = "duration"
      value = var.network_disruption_duration
    }

    parameter {
      key   = "scope"
      value = "all"
    }
  }

  target {
    name           = "private-subnets-in-az"
    resource_type  = "aws:ec2:subnet"
    selection_mode = "ALL"

    resource_tag {
      key   = local.project_tag.key
      value = local.project_tag.value
    }

    # Set by infra/modules/network on private subnets only.
    resource_tag {
      key   = "kubernetes.io/role/internal-elb"
      value = "1"
    }

    filter {
      path   = "AvailabilityZone"
      values = [var.disrupted_availability_zone]
    }
  }

  tags = {
    Name = "${var.cluster_name}-az-network-disruption"
  }
}
