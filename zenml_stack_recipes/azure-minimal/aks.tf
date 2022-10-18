data "azurerm_kubernetes_cluster" "cluster" {
  name                = azurerm_kubernetes_cluster.aks.name
  resource_group_name = azurerm_resource_group.rg.name
  depends_on = [
    azurerm_kubernetes_cluster.aks
  ]
}

resource "azurerm_kubernetes_cluster" "aks" {
  name                = "${local.prefix}-${local.aks.cluster_name}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  dns_prefix          = local.prefix

  default_node_pool {
    name    = "default"
    vm_size = "Standard_D2_v2"

    enable_auto_scaling = true
    max_count           = 3
    min_count           = 1
    node_count          = 2
  }

  identity {
    type = "SystemAssigned"
  }

  tags = local.tags
}

resource "kubernetes_namespace" "k8s-ns" {
  metadata {
    name = "zenml"
  }
}