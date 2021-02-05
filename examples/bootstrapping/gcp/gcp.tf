terraform {
  required_providers {
    google-beta = {
      version = "3.54.0"
    }
    kubernetes = {
      version = "~> 2.0"
    }
    random = {
      version = "~> 3.0"
    }
    local = {
      version = "~> 2.0"
    }
  }
}

variable "project" {
  type = string
}
variable "region" {
  type = string
}

// randoms

resource "random_id" "bootstrap_id" {
  byte_length = 4
  prefix = "zenml-"
}

resource "random_shuffle" "google_zone" {
  input = data.google_compute_zones.available.names
  result_count = 1
}

resource "random_password" "password" {
  length = 16
  special = true
  override_special = "_%@"
}

// locals

locals {
  zenml_bootstrapping_id = lower(random_id.bootstrap_id.hex)
  zone_in_region = random_shuffle.google_zone.result[0]
  # change these to adjust your own preferences.
  metadata_instance_type = "db-n1-standard-1"
  # tier for your db. See https://cloud.google.com/sql/pricing for more info
  metadata_user = "metadata"
  metadata_password = random_password.password.result
}

// provider

provider "google-beta" {
  project = var.project
  region = var.region
}

// data

data "google_client_config" "provider" {}

data "google_compute_zones" "available" {
  project = var.project
  region = var.region
}

// resources

resource "google_project_iam_custom_role" "zenml-role" {
  project = var.project
  permissions = ["cloudsql.instances.connect", "cloudsql.instances.get", "storage.buckets.create", "storage.buckets.delete", "storage.buckets.get", "storage.buckets.getIamPolicy", "storage.buckets.list", "storage.buckets.setIamPolicy", "storage.buckets.update", "storage.objects.create", "storage.objects.delete", "storage.objects.get", "storage.objects.getIamPolicy", "storage.objects.list", "storage.objects.setIamPolicy", "storage.objects.update"]
  role_id = "ZenMLRole"
  title = "A custom role for ZenML to ensure permissions for Storage, Metadata."
}

resource "google_service_account" "zenml" {
  project = var.project
  account_id = "zenml-gke-sql"
  display_name = "ZenML service account for Kubernetes and SQL"
}

resource "google_project_iam_binding" "zenml-role" {
  project = var.project
  members = [
    "serviceAccount:${google_service_account.zenml.email}"
  ]
  role = google_project_iam_custom_role.zenml-role.id
}

resource "google_service_account_key" "zenml_key" {
  service_account_id = google_service_account.zenml.name
}

resource "google_sql_database" "database" {
  project = var.project
  name = "${local.zenml_bootstrapping_id}-metadata"
  instance = google_sql_database_instance.metadata_store.name
}

resource "google_sql_database_instance" "metadata_store" {
  project = var.project
  region = var.region
  name = "${local.zenml_bootstrapping_id}-metadata"
  database_version = "MYSQL_5_7"

  settings {
    # For more information please visit https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/sql_database_instance#settings
    tier = local.metadata_instance_type
  }

  deletion_protection = false
}

resource "google_sql_user" "zenml" {
  project = var.project
  name = local.metadata_user
  password = local.metadata_password
  instance = google_sql_database_instance.metadata_store.name
  host = "%"
}

resource "google_storage_bucket" "artifact_store" {
  project = var.project
  name = local.zenml_bootstrapping_id
  location = upper(var.region)
}

resource "google_container_cluster" "gke" {
  project = var.project
  name = local.zenml_bootstrapping_id
  location = local.zone_in_region

  enable_intranode_visibility = true

  ip_allocation_policy {
    cluster_ipv4_cidr_block = ""
    services_ipv4_cidr_block = ""
  }

  //  networking_mode = VPC_NATIVE
  enable_tpu = true
  network_policy {
    enabled = true
  }
  addons_config {
    network_policy_config {
      disabled = false
    }
  }

  # We can't create a cluster with no node pool defined, but we want to only use
  # separately managed node pools. So we create the smallest possible default
  # node pool and immediately delete it.
  remove_default_node_pool = true
  initial_node_count = 1
}

resource "google_container_node_pool" "gke_nodes" {
  project = var.project
  name = local.zenml_bootstrapping_id
  location = local.zone_in_region
  cluster = google_container_cluster.gke.name

  initial_node_count = 1

  lifecycle {
    ignore_changes = [
      initial_node_count
    ]
  }

  autoscaling {
    max_node_count = 5
    min_node_count = 1
  }

  node_config {
    //    preemptible  = true
    machine_type = "e2-medium"

    oauth_scopes = [
      "https://www.googleapis.com/auth/bigquery",
      "https://www.googleapis.com/auth/cloud-platform",
      "https://www.googleapis.com/auth/source.full_control",
      "https://www.googleapis.com/auth/compute",
      "https://www.googleapis.com/auth/datastore",
      "https://www.googleapis.com/auth/devstorage.read_only",
      "https://www.googleapis.com/auth/logging.write",
      "https://www.googleapis.com/auth/monitoring.write",
      "https://www.googleapis.com/auth/pubsub",
      "https://www.googleapis.com/auth/service.management.readonly",
      "https://www.googleapis.com/auth/servicecontrol",
      "https://www.googleapis.com/auth/trace.append",
      "https://www.googleapis.com/auth/devstorage.read_only",
      "https://www.googleapis.com/auth/logging.write",
      "https://www.googleapis.com/auth/monitoring",
      "https://www.googleapis.com/auth/service.management.readonly",
      "https://www.googleapis.com/auth/servicecontrol",
      "https://www.googleapis.com/auth/trace.append",
      "https://www.googleapis.com/auth/logging.write",
      "https://www.googleapis.com/auth/monitoring",
      "https://www.googleapis.com/auth/monitoring.read",
      "https://www.googleapis.com/auth/monitoring.write",
      "https://www.googleapis.com/auth/pubsub",
      "https://www.googleapis.com/auth/servicecontrol",
      "https://www.googleapis.com/auth/service.management.readonly",
      "https://www.googleapis.com/auth/sqlservice",
      "https://www.googleapis.com/auth/sqlservice.admin",
      "https://www.googleapis.com/auth/devstorage.full_control",
      "https://www.googleapis.com/auth/devstorage.read_only",
      "https://www.googleapis.com/auth/devstorage.read_write",
      "https://www.googleapis.com/auth/taskqueue",
      "https://www.googleapis.com/auth/trace.append",
      "https://www.googleapis.com/auth/userinfo.email",
    ]
  }
}

provider "kubernetes" {

  host = "https://${google_container_cluster.gke.endpoint}"
  token = data.google_client_config.provider.access_token
  cluster_ca_certificate = base64decode(
  google_container_cluster.gke.master_auth[0].cluster_ca_certificate,
  )
}

resource "kubernetes_secret" "google-application-credentials" {
  metadata {
    name = "google-application-credentials"
  }
  data = {
    "key.json" = base64decode(google_service_account_key.zenml_key.private_key)
  }
}

resource "kubernetes_deployment" "cloudsql" {
  metadata {
    name = "cloudsql"

    labels = {
      app = "cloudsql"
    }
  }

  spec {
    replicas = 1

    selector {
      match_labels = {
        app = "cloudsql"
      }
    }

    template {
      metadata {
        labels = {
          app = "cloudsql"
        }
      }

      spec {
        volume {
          name = "google-application-credentials"

          secret {
            secret_name = kubernetes_secret.google-application-credentials.metadata[0].name
          }
        }

        container {
          name = "cloudsql"
          image = "gcr.io/cloudsql-docker/gce-proxy:1.10"
          command = [
            "/cloud_sql_proxy",
            "-instances=${google_sql_database_instance.metadata_store.connection_name}=tcp:0.0.0.0:3306",
            "-credential_file=/secrets/cloudsql/key.json"]

          volume_mount {
            name = "google-application-credentials"
            read_only = true
            mount_path = "/secrets/cloudsql"
          }
        }
      }
    }
  }

  depends_on = [
    google_container_node_pool.gke_nodes]
}

resource "kubernetes_service" "sql_proxy_service" {
  metadata {
    name = "sql-proxy-service"
  }

  spec {
    port {
      protocol = "TCP"
      port = 3306
      target_port = "3306"
    }

    selector = {
      app = "cloudsql"
    }
  }
}

// outputs

output "ZenML" {
  value = <<-EOT
  You successfully bootstrapped ZenML on GCP.

  ---
  Your Google Cloud SQL Metadata Store has been successfully bootstrapped.

  Connection details:
    connection_name: ${google_sql_database_instance.metadata_store.connection_name}
    SQL user: ${local.metadata_user}
    SQL password: ${local.metadata_password}

  To launch a local Docker CloudSQL Proxy, run this command:

    docker run -d \
      -p 127.0.0.1:3306:3306 \
      --name ${local.zenml_bootstrapping_id} gcr.io/cloudsql-docker/gce-proxy:1.16 /cloud_sql_proxy \
      -instances=${google_sql_database_instance.metadata_store.connection_name}=tcp:0.0.0.0:3306 \
      -token=$(gcloud auth application-default print-access-token)

  ---
  Your Google Cloud Storage Artifact Store has been successfully bootstrapped.

    Path: ${google_storage_bucket.artifact_store.url}

  ---
  Your Google Kubernetes Engine Cluster has been successfully bootstrapped.

  To connect to your cluster from your local kubectl run:

    gcloud container clusters get-credentials ${local.zenml_bootstrapping_id}

  ---
  To configure your local ZenML project with these resources, follow these steps:

  0. Initialize ZenML locally (optional, only if you have not done so already):
    zenml init

  1. Create & start the CloudSQL proxy:
    docker run -d \
      -p 127.0.0.1:3306:3306 \
      --name ${local.zenml_bootstrapping_id} gcr.io/cloudsql-docker/gce-proxy:1.16 /cloud_sql_proxy \
      -instances=${google_sql_database_instance.metadata_store.connection_name}=tcp:0.0.0.0:3306 \
      -token=$(gcloud auth application-default print-access-token)

  2. Configure the Metadata Store:
    zenml config metadata set mysql \
      --host="127.0.0.1" \
      --port="3306" \
      --username="${local.metadata_user}" \
      --password="${local.metadata_password}" \
      --database="zenml"

  3. Configure the Artifact Store:
    zenml config artifacts set "${google_storage_bucket.artifact_store.url}"

  ---
  To provision ZenML with your bootstrapped resources run:

    ./setup.sh
EOT
}

resource "local_file" "zenml_setup" {
  filename = "setup.sh"
  content = <<-EOF
  #!/usr/bin/env bash
  set -euo pipefail
  IFS=$'\n\t'

  #/ Usage: ./setup.sh
  #/ Description: Simply run ./setup.sh to configure your local system with the newly bootstrapped resources.
  #/ Examples: ./setup.sh
  #/ Options:
  #/   --help: Display this help message
  usage() { grep '^#/' "$0" | cut -c4- ; exit 0 ; }
  expr "$*" : ".*--help" > /dev/null && usage

  echoerr() { printf "%s\n" "$*" >&2 ; }
  info()    { echoerr "[INFO]    $*" ; }
  warning() { echoerr "[WARNING] $*" ; }
  error()   { echoerr "[ERROR]   $*" ; }
  fatal()   { echoerr "[FATAL]   $*" ; exit 1 ; }

  cleanup() {
    # Remove temporary files
    # Restart services
    info "... cleaned up"
  }

  if [[ "$${BASH_SOURCE[0]}" = "$0" ]]; then
    trap cleanup EXIT
    info "starting script ..."

    # zenml init if not done already
    zenml init --analytics_opt_in FALSE > /dev/null 2>&1 && info "ZenML initialized" || info "ZenML already initialized - skipping"

    # docker cloud sql proxy
    docker run -d \
      -p 127.0.0.1:3306:3306 \
      --name ${local.zenml_bootstrapping_id} gcr.io/cloudsql-docker/gce-proxy:1.16 /cloud_sql_proxy \
      -instances=${google_sql_database_instance.metadata_store.connection_name}=tcp:0.0.0.0:3306 \
      -token=$(gcloud auth application-default print-access-token)
    info "Cloud SQL Proxy configured."
    info "To start run: docker start ${local.zenml_bootstrapping_id}"
    info "To stop run: docker stop ${local.zenml_bootstrapping_id}"

    # zenml configurations
    zenml config metadata set mysql \
      --host="127.0.0.1" \
      --port="3306" \
      --username="${local.metadata_user}" \
      --password="${local.metadata_password}" \
      --database="zenml"
    zenml config artifacts set "${google_storage_bucket.artifact_store.url}"

    info "successfully configured ZenML with your boostrapped resources."
  fi

EOF
}