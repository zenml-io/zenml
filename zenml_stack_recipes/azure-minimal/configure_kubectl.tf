# set up local kubectl client to access the newly created cluster
resource "null_resource" "configure-local-kubectl" {
  provisioner "local-exec" {
    command = "az aks get-credentials --resource-group ${azurerm_resource_group.rg.name} --name ${local.prefix}-${local.aks.cluster_name} --context ${local.kubectl_context} --overwrite-existing"
  }
  depends_on = [
    azurerm_kubernetes_cluster.aks
  ]
}

locals {
  kubectl_context = "terraform-${local.prefix}-${local.aks.cluster_name}-${replace(substr(timestamp(), 0, 16), ":", "_")}"
}