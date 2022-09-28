# set up the nginx ingress controller
resource "kubernetes_namespace" "nginx-ns" {
  metadata {
    name = "ingress-nginxhihi"
  }
}

resource "helm_release" "nginx-controller" {
  name       = "zenml"
  count      = var.create_ingress_controller? 1 : 0
  repository = "https://kubernetes.github.io/ingress-nginx"
  chart      = "ingress-nginx"
  # dependency on nginx-ns
  namespace = kubernetes_namespace.nginx-ns.metadata[0].name
}

data "kubernetes_service" "ingress-controller" {
  metadata {
    name      = "zenml-ingress-nginx-controller"
    namespace = kubernetes_namespace.nginx-ns.metadata[0].name
  }
  depends_on = [
    resource.helm_release.nginx-controller
  ]
}