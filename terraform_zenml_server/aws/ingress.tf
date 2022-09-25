# set up the nginx ingress controller
resource "kubernetes_namespace" "nginx-ns" {
  metadata {
    name = "ingress-nginx"
  }
}

resource "helm_release" "nginx-controller" {
  name       = "nginx-controller"
  repository = "https://kubernetes.github.io/ingress-nginx"
  chart      = "ingress-nginx"
  # dependency on nginx-ns
  namespace = kubernetes_namespace.nginx-ns.metadata[0].name
}