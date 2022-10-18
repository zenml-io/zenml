# get URI for  MLflow tracking server
data "kubernetes_service" "mlflow_tracking" {
  metadata {
    name      = "${module.mlflow.ingress-controller-name}-ingress-nginx-controller"
    namespace = module.mlflow.ingress-controller-namespace
  }

  depends_on = [
    module.mlflow
  ]
}

# get the ingress host URL for the seldon model deployer
data "kubernetes_service" "seldon_ingress" {
  metadata {
    name      = "istio-ingress-seldon"
    namespace = "istio-ingress"
  }

  depends_on = [
    module.seldon
  ]
}