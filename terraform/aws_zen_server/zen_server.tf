# create the ZenServer deployment
resource "helm_release" "zen-server" {

  name       = "zenml-server"
  repository = "../../helm"
  chart      = "zenml"

  # set workload identity annotations for the mlflow 
  # kubernetes service account
  set {
    name  = "zenml.database.url"
    value = local.rds.create_rds? module.metadata_store.db_instance_address : local.rds.hostname
  }

  # set proxied access to artifact storage
  set {
    name  = "zenml.database.sslCa"
    value = local.rds.create_rds? "./ca.pem" : local.rds.server_ca
  }

  # set values for S3 artifact store
  set {
    name  = "zenml.database.sslCert"
    value = local.rds.create_rds? "./cert.pem" : local.rds.client_cert
  }
  set {
    name  = "zenml.database.sslKey"
    value = local.rds.create_rds? "./key.pem" : local.rds.client_key
  }
  set {
    name  = "zenml.database.sslVerifyServerCert"
    value = true
  }
}