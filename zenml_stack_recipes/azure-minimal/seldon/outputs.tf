output "ingress-gateway-spec" {
  value = kubectl_manifest.gateway.live_manifest_incluster
}