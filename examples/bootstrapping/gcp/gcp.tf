terraform {
  required_providers {
    gcp = {
      version = "3.54.0"
    }
  }
}

variable "project" {
  type = string
}
variable "region" {
  type = string
}

locals {
  # change these to adjust your own preferences.
  metadata_instance_type = "db-n1-standard-1"  # tier for your db. See https://cloud.google.com/sql/pricing for more info
}

provider "google" {
  project     = var.project
  region      = var.region
}

data "google_client_config" "provider" {}


resource "random_id" "bootstrap_id" {
  byte_length = 8
  prefix = "zenml-"
}

resource "google_service_account" "zenml" {
  account_id   = "zenml"
  display_name = "ZenML service account"
}

resource "google_service_account_key" "zenml_key" {
  service_account_id = google_service_account.zenml.name
}

resource "google_sql_database_instance" "metadata_store" {
  name             = "master-instance"
  database_version = "MYSQL_5_7"

  settings {
    # For more information please visit https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/sql_database_instance#settings
    tier = local.metadata_instance_type
  }
}

resource "google_storage_bucket" "artifact_store" {
  name          = random_id.bootstrap_id.b64_url
  location      = upper(var.region)
}

resource "google_container_cluster" "gke" {
  name     = random_id.bootstrap_id.b64_url
  location = var.region

  enable_intranode_visibility = true
  ip_allocation_policy = {}
  networking_mode = "VPC_NATIVE"
  enable_tpu = true
  network_policy = {
    enabled = true
  }
  network_policy_config = {
    disabled = false
  }


  # We can't create a cluster with no node pool defined, but we want to only use
  # separately managed node pools. So we create the smallest possible default
  # node pool and immediately delete it.
  remove_default_node_pool = true
  initial_node_count       = 1
}

resource "google_container_node_pool" "gke_nodes" {
  name       = random_id.bootstrap_id.b64_url
  location   = var.region
  cluster    = google_container_cluster.gke.name
  autoscaling {
    max_node_count = 5
    min_node_count = 1
  }

  node_config {
//    preemptible  = true
    machine_type = "e2-medium"

    #
    oauth_scopes    = [
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
  load_config_file = false

  host  = "https://${google_container_cluster.gke.endpoint}"
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
            secret_name = kubernetes_secret.google-application-credentials.metadata.name
          }
        }

        container {
          name    = "cloudsql"
          image   = "gcr.io/cloudsql-docker/gce-proxy:1.10"
          command = ["/cloud_sql_proxy", "-instances=${google_sql_database_instance.metadata_store.connection_name}=tcp:0.0.0.0:3306", "-credential_file=/secrets/cloudsql/key.json"]

          volume_mount {
            name       = "google-application-credentials"
            read_only  = true
            mount_path = "/secrets/cloudsql"
          }
        }
      }
    }
  }
}

resource "kubernetes_service" "sql_proxy_service" {
  metadata {
    name = "sql-proxy-service"
  }

  spec {
    port {
      protocol    = "TCP"
      port        = 3306
      target_port = "3306"
    }

    selector = {
      app = "cloudsql"
    }
  }
}
