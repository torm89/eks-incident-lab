locals {
  start_experiment_command = "aws fis start-experiment --profile <aws-profile> --region eu-west-1 --experiment-template-id"
}

output "start_node_spot_interruption" {
  description = "Command that starts the spot interruption experiment."
  value       = "${local.start_experiment_command} ${aws_fis_experiment_template.node_spot_interruption.id}"
}

output "start_node_terminate" {
  description = "Command that starts the node termination experiment."
  value       = "${local.start_experiment_command} ${aws_fis_experiment_template.node_terminate.id}"
}

output "start_az_network_disruption" {
  description = "Command that starts the availability zone network disruption experiment."
  value       = "${local.start_experiment_command} ${aws_fis_experiment_template.az_network_disruption.id}"
}
