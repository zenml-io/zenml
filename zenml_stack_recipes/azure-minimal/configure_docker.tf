# set up local docker client to access the newly created registry
resource "null_resource" "configure-local-docker" {
  provisioner "local-exec" {
    command = "az acr login --name ${azurerm_container_registry.container_registry.name}"
  }
  depends_on = [
    azurerm_container_registry.container_registry
  ]
}