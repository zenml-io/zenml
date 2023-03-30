data "azurerm_client_config" "current" {}

# run kubectl config view commands to get the current cluster and rg
resource "null_resource" "get_cluster_and_rg" {
  provisioner "local-exec" {
    command = "kubectl config view --minify -o jsonpath='{.clusters[].name}' > cluster.txt"
  }
  provisioner "local-exec" {
    command = "kubectl config view --minify -o jsonpath='{.contexts[].context.user}' | cut -d_ -f2 > namespace.txt"
  }
}

# get the current cluster and namespace
data "local_file" "cluster" {
  filename = "cluster.txt"
}

data "local_file" "rg" {
  filename = "namespace.txt"
}

# get the current cluster and namespace
locals {
  cluster   = data.local_file.cluster.content
  rg = data.local_file.rg.content
}

data "azurerm_kubernetes_cluster" "current" {
  name                = local.cluster
  resource_group_name = local.rg
}

# create a key vault instance that can be used for storing secrets
resource "azurerm_key_vault" "secret_manager" {
  name                        = "${var.key_vault_name}-${random_string.unique.result}"
  location                    = azurerm_resource_group.rg.location
  resource_group_name         = azurerm_resource_group.rg.name
  enabled_for_disk_encryption = true
  tenant_id                   = data.azurerm_client_config.current.tenant_id
  soft_delete_retention_days  = 7
  purge_protection_enabled    = false

  sku_name = "standard"

  access_policy {
    tenant_id = data.azurerm_client_config.current.tenant_id
    object_id = data.azurerm_client_config.current.object_id

    key_permissions = [
      "Get", "List", "Create", "Delete", "Update"
    ]

    secret_permissions = [
      "Get", "List", "Delete"
    ]

    storage_permissions = [
      "Get", "List", "Set", "Delete", "Update"
    ]
  }
}


resource "azurerm_key_vault_access_policy" "kv-access" {
  key_vault_id = azurerm_key_vault.secret_manager.id
  tenant_id    = data.azurerm_kubernetes_cluster.current.azure_active_directory_role_based_access_control.0.tenant_id
  object_id    = data.azurerm_kubernetes_cluster.current.kubelet_identity.0.object_id

  key_permissions = [
    "Get", "List", "Create", "Delete", "Update"
  ]

  secret_permissions = [
    "Get", "List", "Set", "Delete"
  ]

  storage_permissions = [
    "Get", "List", "Set", "Delete", "Update"
  ]
}

resource "azurerm_key_vault_access_policy" "kv-access-user" {
  key_vault_id = azurerm_key_vault.secret_manager.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = data.azurerm_client_config.current.object_id

  key_permissions = [
    "Get", "List", "Create", "Delete", "Update"
  ]

  secret_permissions = [
    "Get", "List", "Set", "Delete"
  ]

  storage_permissions = [
    "Get", "List", "Set", "Delete", "Update"
  ]
}