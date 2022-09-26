# set up the nginx ingress controller
resource "kubernetes_namespace" "nginx-ns" {
  metadata {
    name = "ingress-nginx"
  }

  depends_on = [
    null_resource.configure-local-kubectl
  ]
}

resource "helm_release" "nginx-controller" {
  name       = "nginx-controller"
  count      = var.create_ingress_controller? 1 : 0
  repository = "https://kubernetes.github.io/ingress-nginx"
  chart      = "ingress-nginx"
  # dependency on nginx-ns
  namespace = kubernetes_namespace.nginx-ns.metadata[0].name
}