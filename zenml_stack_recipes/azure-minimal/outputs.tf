# Resource Group
output "resource-group-name" {
  value = azurerm_resource_group.rg.name
}

# output for the AKS cluster
output "aks-cluster-name" {
  value = "${local.prefix}-${local.aks.cluster_name}"
}

# output for the Blob Storage Container
output "blobstorage-container-path" {
  value       = "az://${azurerm_storage_container.artifact-store.name}"
  description = "The Azure Blob Storage Container path for storing your artifacts"
}
output "storage-account-name" {
  value       = local.blob_storage.account_name
  description = "The name of the Azure Blob Storage account name"
}
output "storage-account-key" {
  value       = data.azurerm_storage_account.zenml-account.primary_access_key
  sensitive   = true
  description = "The Azure Blob Storage account key"
}

# output for container registry
output "container-registry-URL" {
  value = azurerm_container_registry.container_registry.login_server
}

# key-vault name
output "key-vault-name" {
  value = azurerm_key_vault.secret_manager.name
}

# outputs for the MLflow tracking server
output "ingress-controller-name" {
  value = module.mlflow.ingress-controller-name
}
output "ingress-controller-namespace" {
  value = module.mlflow.ingress-controller-namespace
}
output "mlflow-tracking-URL" {
  value = data.kubernetes_service.mlflow_tracking.status.0.load_balancer.0.ingress.0.ip
}

# output for seldon model deployer
output "seldon-core-workload-namespace" {
  value       = kubernetes_namespace.seldon-workloads.metadata[0].name
  description = "The namespace created for hosting your Seldon workloads"
}
output "seldon-prediction-spec" {
  value     = module.seldon.ingress-gateway-spec
  sensitive = true
}
output "seldon-base-url" {
  value = data.kubernetes_service.seldon_ingress.status.0.load_balancer.0.ingress.0.ip
}

# output the name of the stack YAML file created
output "stack-yaml-path" {
  value = local_file.stack_file.filename
}