output "zenml_server_url" {
  value = var.create_ingress_controller ? "https://zenml.${data.kubernetes_service.ingress-controller[0].status.0.load_balancer.0.ingress.0.ip}.nip.io" : "https://zenml.${var.ingress_controller_ip}.nip.io"
}
output "ca_crt" {
  value     = base64decode(data.kubernetes_secret.certificates.binary_data["ca.crt"])
  sensitive = true
}
