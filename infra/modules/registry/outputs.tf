output "repository_urls" {
  description = "Repository URL per service name."
  value       = { for name, repository in aws_ecr_repository.this : name => repository.repository_url }
}
