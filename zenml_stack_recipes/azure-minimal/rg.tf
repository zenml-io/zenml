resource "azurerm_resource_group" "rg" {
  name     = "${local.prefix}-${local.resource_group.name}"
  location = local.resource_group.location
}