# The template is free. You pay only while the experiment runs (about $0.10 per action-minute).
resource "aws_fis_experiment_template" "this" {
  description = "Cut all network traffic of the private subnets in one availability zone"
  role_arn    = module.fis_role.arn

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
      value = var.duration
    }

    parameter {
      key   = "scope"
      value = "all"
    }
  }

  # Found by tags at start time, so the template can exist before the cluster.
  target {
    name           = "private-subnets-in-az"
    resource_type  = "aws:ec2:subnet"
    selection_mode = "ALL"

    # infra/ tags every resource with Project=torm-eks.
    resource_tag {
      key   = "Project"
      value = "torm-eks"
    }

    # Set by infra/modules/network on private subnets only.
    resource_tag {
      key   = "kubernetes.io/role/internal-elb"
      value = "1"
    }

    filter {
      path   = "AvailabilityZone"
      values = [var.availability_zone]
    }
  }

  tags = {
    Name = "${var.cluster_name}-az-network-disruption"
  }
}
