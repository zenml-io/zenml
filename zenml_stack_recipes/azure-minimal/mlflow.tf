# using the mlflow module to create an mlflow deployment
module "mlflow" {
  source = "./mlflow-module"

  # run only after the eks cluster is set up
  depends_on = [azurerm_kubernetes_cluster.aks]

  # details about the mlflow deployment
  htpasswd                            = "${var.mlflow-username}:${htpasswd_password.hash.apr1}"
  artifact_Proxied_Access             = local.mlflow.artifact_Proxied_Access
  artifact_Azure                      = local.mlflow.artifact_Azure
  artifact_Azure_Storage_Account_Name = local.mlflow.artifact_Azure_Storage_Account_Name == "" ? azurerm_storage_account.zenml-account.name : local.mlflow.artifact_Azure_Storage_Account_Name
  artifact_Azure_Container            = local.mlflow.artifact_Azure_Storage_Account_Name == "" ? azurerm_storage_container.artifact-store.name : local.mlflow.artifact_Azure_Container
  artifact_Azure_Access_Key           = local.mlflow.artifact_Azure_Storage_Account_Name == "" ? data.azurerm_storage_account.zenml-account.primary_access_key : var.mlflow-artifact-Azure-Access-Key
}

resource "htpasswd_password" "hash" {
  password = var.mlflow-password
}