# set up the nginx ingress controller
resource "kubernetes_namespace" "nginx-ns" {
  count = var.create_ingress_controller ? 1 : 0
  metadata {
    name = "${var.name}-ingress"
  }
}

resource "helm_release" "nginx-controller" {
  name       = "zenml"
  count      = var.create_ingress_controller ? 1 : 0
  repository = "https://kubernetes.github.io/ingress-nginx"
  chart      = "ingress-nginx"
  # dependency on nginx-ns
  namespace = var.create_ingress_controller ? kubernetes_namespace.nginx-ns[0].metadata[0].name : ""
  depends_on = [
    resource.kubernetes_namespace.nginx-ns
  ]
}

data "kubernetes_service" "ingress-controller" {
  count = var.create_ingress_controller ? 1 : 0
  metadata {
    name      = "zenml-ingress-nginx-controller"
    namespace = var.create_ingress_controller ? kubernetes_namespace.nginx-ns[0].metadata[0].name : ""
  }
  depends_on = [
    resource.helm_release.nginx-controller
  ]
}