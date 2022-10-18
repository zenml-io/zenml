# config values to use across the module
locals {
  prefix = "demo"
  region = "us-west1"

  resource_group = {
    name     = "zenml-demos"
    location = "West Europe"
  }
  aks = {
    cluster_name = "zenml-terraform-cluster"
    # important to use 1.22 or above due to a bug with Istio in older versions
    cluster_version      = "1.23.5"
    orchestrator_version = "1.23.5"
  }
  vpc = {
    name = "zenmlvpc"
  }

  blob_storage = {
    account_name   = "zenmlaccount"
    container_name = "zenmlartifactstore"
  }

  acr = {
    name = "zenmlcontainerregistry"
  }

  mysql = {
    name = "zenmlmetadata"
  }

  key_vault = {
    name = "zenmlsecrets"
  }

  seldon = {
    name      = "seldon"
    namespace = "seldon-system"
  }
  mlflow = {
    artifact_Proxied_Access = "false"
    artifact_Azure          = "true"
    # if not set, the container created as part of the deployment will be used
    artifact_Azure_Storage_Account_Name = ""
    # this field is considered only when the storage account above is set
    artifact_Azure_Container = ""
  }

  tags = {
    "managedBy"   = "terraform"
    "application" = local.prefix
  }
}