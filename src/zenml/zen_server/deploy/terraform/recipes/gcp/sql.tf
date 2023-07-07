# random string for the CloudSQL instance name
resource "random_string" "cloudsql_suffix" {
  count  = var.deploy_db ? 1 : 0
  length = 4
  upper  = false
  special = false
}

module "metadata_store" {
  source  = "GoogleCloudPlatform/sql-db/google//modules/mysql"
  version = "11.0.0"
  count   = var.deploy_db ? 1 : 0

  project_id       = var.project_id
  name             = "${var.name}-${var.cloudsql_name}-${random_string.cloudsql_suffix[0].result}"
  db_name          = var.db_name
  database_version = "MYSQL_5_7"
  disk_size        = var.db_disk_size
  tier             = var.db_instance_tier
  region           = var.region
  zone             = "${var.region}-c"

  user_name     = var.database_username
  user_password = var.database_password

  deletion_protection = false

  ip_configuration = {
    authorized_networks = [
      {
        name  = "all",
        value = "0.0.0.0/0"
      }
    ]
    ipv4_enabled       = true
    private_network    = null
    require_ssl        = false
    allocated_ip_range = null
  }
}

# create the client certificate for CloudSQL
resource "google_sql_ssl_cert" "client_cert" {
  count       = var.deploy_db ? 1 : 0
  common_name = "sql-cert"
  instance    = module.metadata_store[0].instance_name
}

# create the certificate files
resource "local_file" "server-ca" {
  count    = var.deploy_db ? 1 : 0
  content  = google_sql_ssl_cert.client_cert[0].server_ca_cert
  filename = "./server-ca.pem"
}
resource "local_file" "client-cert" {
  count    = var.deploy_db ? 1 : 0
  content  = google_sql_ssl_cert.client_cert[0].cert
  filename = "./client-cert.pem"
}
resource "local_file" "client-key" {
  count    = var.deploy_db ? 1 : 0
  content  = google_sql_ssl_cert.client_cert[0].private_key
  filename = "./client-key.pem"
}