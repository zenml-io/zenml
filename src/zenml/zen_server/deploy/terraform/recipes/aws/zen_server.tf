# create the ZenML Server deployment
resource "kubernetes_namespace" "zen-server" {
  metadata {
    name = "${var.name}-${var.namespace}"
  }
}

resource "helm_release" "zen-server" {

  name      = "${var.name}-zenmlserver"
  chart     = var.helm_chart
  namespace = kubernetes_namespace.zen-server.metadata[0].name

  set {
    name  = "zenml.image.repository"
    value = var.zenmlserver_image_repo
  }
  set {
    name  = "zenml.image.tag"
    value = var.zenmlserver_image_tag
  }
  set {
    name  = "zenml.defaultUsername"
    value = var.username
  }
  set {
    name  = "zenml.defaultPassword"
    value = var.password
  }
  set {
    name  = "zenml.deploymentType"
    value = "aws"
  }

  set {
    name  = "zenml.secretsStore.type"
    value = "aws"
  }
  set {
    name  = "zenml.secretsStore.aws.region_name"
    value = var.region
  }

  set {
    name = "zenml.analyticsOptIn"
    value = var.analytics_opt_in
  }
  
  # set up the right path for ZenML
  set {
    name  = "zenml.ingress.annotations.nginx\\.ingress\\.kubernetes\\.io/rewrite-target"
    value = ""
  }
  set {
    name  = "zenml.ingress.host"
    value = var.create_ingress_controller ? "${data.kubernetes_service.ingress-controller[0].status.0.load_balancer.0.ingress.0.hostname}" : "zenml.${var.ingress_controller_ip}.nip.io"
  }
  set {
    name  = "zenml.ingress.tls.enabled"
    value = var.ingress_tls
  }
  set {
    name  = "zenml.ingress.tls.generateCerts"
    value = var.ingress_tls_generate_certs
  }
  set {
    name  = "zenml.ingress.tls.secretName"
    value = "${var.name}-${var.ingress_tls_secret_name}"
  }

  # set parameters for the mysql database
  set {
    name  = "zenml.database.url"
    value = var.deploy_db ? "mysql://${module.metadata_store[0].db_instance_username}:${module.metadata_store[0].db_instance_password}@${module.metadata_store[0].db_instance_address}:3306/${var.db_name}" : var.database_url
  }
  set {
    name  = "zenml.database.sslCa"
    value = var.deploy_db ? "" : var.database_ssl_ca
  }
  set {
    name  = "zenml.database.sslCert"
    value = var.deploy_db ? "" : var.database_ssl_cert
  }
  set {
    name  = "zenml.database.sslKey"
    value = var.deploy_db ? "" : var.database_ssl_key
  }
  set {
    name  = "zenml.database.sslVerifyServerCert"
    value = var.deploy_db ? false : var.database_ssl_verify_server_cert
  }
  depends_on = [
    resource.kubernetes_namespace.zen-server
  ]
}

data "kubernetes_secret" "certificates" {
  metadata {
    name      = "${var.name}-${var.ingress_tls_secret_name}"
    namespace = "${var.name}-${var.namespace}"
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