# create the ZenServer deployment
resource "helm_release" "zen-server" {

  name             = "zenml-server"
  repository       = "../../helm"
  chart            = "zenml"
  namespace        = var.zenmlserver_namespace
  create_namespace = true

  # set workload identity annotations for the mlflow 
  # kubernetes service account
  set {
    name  = "zenml.database.url"
    value = var.create_rds? module.metadata_store[0].db_instance_address : var.rds_url
  }

  # set proxied access to artifact storage
  set {
    name  = "zenml.database.sslCa"
    value = var.create_rds? "./ca.pem" : var.rds_sslCa
  }

  # set values for S3 artifact store
  set {
    name  = "zenml.database.sslCert"
    value = var.create_rds? "./cert.pem" : var.rds_sslCert
  }
  set {
    name  = "zenml.database.sslKey"
    value = var.create_rds? "./key.pem" : var.rds_sslKey
  }
  set {
    name  = "zenml.database.sslVerifyServerCert"
    value = var.create_rds? false : true
  }
}