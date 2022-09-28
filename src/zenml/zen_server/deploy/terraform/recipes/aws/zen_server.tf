# create the ZenServer deployment
resource "helm_release" "zen-server" {

  name             = "${var.name}-zenmlserver"
  chart            = var.helm_chart
  namespace        = "${var.name}-${var.zenmlserver_namespace}"
  create_namespace = true


  set {
    name  = "zenml.defaultUsername"
    value = var.username
  }
  set {
    name  = "zenml.defaultPassword"
    value = var.password
  }
  set {
    name  = "zenml.defaultUserEmail"
    value = var.email
  }
  
  # set up the right path for ZenML
  set {
    name  = "zenml.rootUrlPath"
    value = var.ingress_path != ""? "/${var.ingress_path}": ""
  }
  set {
    name = "ingress.path"
    value = var.ingress_path != ""? "/${var.ingress_path}/?(.*)": "/"
  }
  set {
    name = "ingress.annotations.nginx\\.ingress\\.kubernetes\\.io/rewrite-target"
    value = var.ingress_path != ""? "/$1": ""
  }
  set {
    name = "ingress.host"
    value = var.create_ingress_controller? "${data.kubernetes_service.ingress-controller.status.0.load_balancer.0.ingress.0.hostname}" : var.ingress_controller_hostname
  }
  set {
    name = "ingress.tls.enabled"
    value = var.ingress_tls
  }
  set {
    name = "ingress.tls.generateCerts"
    value = var.ingress_tls_generate_certs
  }
  set {
    name = "ingress.tls.secretName"
    value = var.ingress_tls_secret_name
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

data "kubernetes_secret" "certificates" {
  metadata {
    name = "${var.name}-${var.ingress_tls_secret_name}"
    namespace = "${var.name}-${var.zenmlserver_namespace}"
  }
  binary_data = {
    "tls.crt" = ""
    "tls.key" = ""
    "ca.crt"  = ""
  }

  depends_on = [
    helm_release.zen-server
  ]
}