data "aws_iam_policy_document" "fis_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["fis.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "fis" {
  name               = "${var.cluster_name}-fis"
  assume_role_policy = data.aws_iam_policy_document.fis_assume_role.json
}

# AWS-managed policies, one per FIS action family used in experiments.tf.
resource "aws_iam_role_policy_attachment" "fis" {
  for_each = toset([
    "AWSFaultInjectionSimulatorEC2Access",
    "AWSFaultInjectionSimulatorEKSAccess",
    "AWSFaultInjectionSimulatorNetworkAccess",
  ])

  role       = aws_iam_role.fis.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/${each.value}"
}
