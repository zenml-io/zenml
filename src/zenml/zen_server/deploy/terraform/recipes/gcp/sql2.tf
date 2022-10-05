# # resource "google_sql_database_instance" "instance" {
# #   provider = google-beta
# #   count   = var.create_cloudsql? 1 : 0

# #   project          = var.project_id
# #   name             = var.name
# #   database_version = "MYSQL_5_7"
# #   region           = var.region


# #   settings {
# #     tier = "db-f1-micro"
# #     ip_configuration {
# #       authorized_networks  {
# #           name  = "all"
# #           value = "0.0.0.0/0"
# #       }
# #       ipv4_enabled        = true
# #       private_network     = null
# #       require_ssl         = true
# #       allocated_ip_range  = null
# #     }
# #   }
# # }

# resource "google_storage_bucket" "auto-expire" {
#   name          = "auto-expiring-bucket"
#   location      = "US"
#   force_destroy = true
#   project = "var.project_id"

#   lifecycle_rule {
#     condition {
#       age = 3
#     }
#     action {
#       type = "Delete"
#     }
#   }
# }


# resource "google_sql_database_instance" "instance" {
#   name             = "main"
#   database_version = "POSTGRES_14"
#   region           = "us-central1"
#   count   = true? 1 : 0

#   settings {
#     # Second-generation instance tiers are based on the machine
#     # type. See argument reference below.
#     tier = "db-f1-micro"
#   }
  
#   depends_on = [
#     google_storage_bucket.auto-expire
#   ]
# }

# resource "google_sql_user" "user" {
#   name     = var.database_username
#   instance = google_sql_database_instance.instance[0].name
#   host     = google_sql_database_instance.instance[0].ip_address.0.ip_address 
#   password = var.database_password
# }

# # create the client certificate for CloudSQL
# resource "google_sql_ssl_cert" "client_cert" {
#   common_name = "sql-cert"
#   instance    = google_sql_database_instance.instance[0].name
# }

# # create the certificate files
# resource "local_file" "server-ca" {
#   content  = google_sql_ssl_cert.client_cert.server_ca_cert
#   filename = "./server-ca.pem"
# }
# resource "local_file" "client-cert" {
#   content  = google_sql_ssl_cert.client_cert.cert
#   filename = "./client-cert.pem"
# }
# resource "local_file" "client-key" {
#   content  = google_sql_ssl_cert.client_cert.private_key
#   filename = "./client-key.pem"
# }