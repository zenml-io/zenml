output "zenml_server_url" {
  value = data.kubernetes_service.ingress-controller.status != null ? "https://${data.kubernetes_service.ingress-controller.status.0.load_balancer.0.ingress.0.hostname}/${var.ingress_path}/" : ""
}