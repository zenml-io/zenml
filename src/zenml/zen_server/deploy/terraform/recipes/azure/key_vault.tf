data "azurerm_client_config" "current" {}

data "azurerm_kubernetes_cluster" "current" {
  name                = local.cluster
  resource_group_name = local.rg
}

# create a key vault instance that can be used for storing secrets
resource "azurerm_key_vault" "secret_manager" {
  name                        = "${var.key_vault_name}-${random_string.unique.result}"
  location                    = data.azurerm_resource_group.rg.location
  resource_group_name         = local.rg
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
  tenant_id    = data.azurerm_kubernetes_cluster.current.identity.0.tenant_id
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