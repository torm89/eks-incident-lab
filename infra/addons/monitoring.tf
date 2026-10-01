resource "random_password" "grafana_admin" {
  length  = 24
  special = false
}

# Prometheus, Grafana, kube-state-metrics and node-exporter.
resource "helm_release" "kube_prometheus_stack" {
  name             = "kube-prometheus-stack"
  repository       = "https://prometheus-community.github.io/helm-charts"
  chart            = "kube-prometheus-stack"
  version          = "91.8.2"
  namespace        = "monitoring"
  create_namespace = true
  timeout          = 600

  values = [file("${path.module}/values/kube-prometheus-stack.yaml")]

  set_sensitive = [
    {
      name  = "grafana.adminPassword"
      value = random_password.grafana_admin.result
    }
  ]
}
