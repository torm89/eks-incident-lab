output "start_experiment" {
  description = "Command that starts the experiment. Prints the experiment ID."
  value       = "aws fis start-experiment --region eu-west-1 --experiment-template-id ${aws_fis_experiment_template.this.id} --query experiment.id --output text"
}
