# using the seldon module for creating a 
# seldon + istio deployment
module "seldon" {
  source = "./seldon"

  # run only after the aks cluster is set up
  depends_on = [azurerm_kubernetes_cluster.aks]

  # details about the seldon deployment
  seldon_name      = local.seldon.name
  seldon_namespace = local.seldon.namespace

  # details about the cluster (not required since the configuration 
  # in the caller is inherited into the seldon module)
  cluster_endpoint       = ""
  cluster_ca_certificate = ""
  cluster_token          = ""
}

resource "kubernetes_namespace" "seldon-workloads" {
  metadata {
    name = "zenml-seldon-workloads"
  }
}
