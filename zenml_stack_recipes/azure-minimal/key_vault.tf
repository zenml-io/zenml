data "azurerm_client_config" "current" {}

# create a key vault instance that can be used for storing secrets
resource "azurerm_key_vault" "secret_manager" {
  name                        = local.key_vault.name
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
