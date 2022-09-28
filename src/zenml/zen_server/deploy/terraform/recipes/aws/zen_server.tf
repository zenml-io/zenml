# create the ZenServer deployment
resource "helm_release" "zen-server" {

  name             = "zenml-server"
  chart            = var.helm_chart
  namespace        = var.zenmlserver_namespace
  create_namespace = true

  # set up the right path for ZenML
  set {
    name  = "zenml.rootUrlPath"
    value = "/${var.ingress_path}"
  }
  set {
    name = "ingress.path"
    value = "/${var.ingress_path}/?(.*)"
  }
  set {
    name = "ingress.annotations.nginx\\.ingress\\.kubernetes\\.io/rewrite-target"
    value = "/$1"
  }
  set {
    name = "ingress.host"
    value = var.create_ingress_controller? "${data.kubernetes_service.ingress-controller.status.0.load_balancer.0.ingress.0.hostname}" : var.ingress_controller_hostname
  }

  # set parameters for the mysql database
  set {
    name  = "zenml.database.url"
    value = var.create_rds? "mysql://${module.metadata_store[0].db_instance_username}:${module.metadata_store[0].db_instance_password}@${module.metadata_store[0].db_instance_address}:3306/${var.db_name}" : var.rds_url
  }
  set {
    name  = "zenml.database.sslCa"
    value = var.create_rds? "" : var.rds_sslCa
  }
  set {
    name  = "zenml.database.sslCert"
    value = var.create_rds? "" : var.rds_sslCert
  }
  set {
    name  = "zenml.database.sslKey"
    value = var.create_rds? "" : var.rds_sslKey
  }
  set {
    name  = "zenml.database.sslVerifyServerCert"
    value = var.create_rds? false : var.rds_sslVerifyServerCert
  }
}