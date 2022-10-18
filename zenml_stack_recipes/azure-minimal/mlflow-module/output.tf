output "ingress-controller-name" {
  value = helm_release.nginx-controller.name
}
output "ingress-controller-namespace" {
  value = kubernetes_namespace.nginx-ns.metadata[0].name
}