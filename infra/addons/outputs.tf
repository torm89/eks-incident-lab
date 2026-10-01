output "grafana_admin_password" {
  description = "Password of the Grafana 'admin' user."
  value       = random_password.grafana_admin.result
  sensitive   = true
}

output "open_grafana" {
  description = "Command that makes Grafana available at http://localhost:3000."
  value       = "kubectl -n ${helm_release.kube_prometheus_stack.namespace} port-forward svc/kube-prometheus-stack-grafana 3000:80"
}
