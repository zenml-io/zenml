variable "name" {
  description = "The prefix to use for all AWS resource names"
  default     = "zenmlserver"
  type        = string
}

variable "project_id" {
  description = "The project ID in GCP that you want to deploy ZenML to"
  default     = ""
  type        = string
}

variable "region" {
  description = "The region for your GCP resources"
  default     = "europe-west3"
  type        = string
}

variable "namespace" {
  description = "The namespace to install the ZenML server Helm chart in"
  default     = "terraform-server"
  type        = string
}

variable "helm_chart" {
  description = "The path to the ZenML server helm chart"
  default     = "../../../helm"
  type        = string
}

variable "kubectl_config_path" {
  description = "The path to the kube config"
  default     = ""
  type        = string
}

variable "analytics_opt_in" {
  description = "The flag to enable/disable analytics"
  default     = true
  type        = bool
}

# If you want a new CloudSQL, choose a name and a password. If you already
# have an instance, provide the name and the password here too.
variable "database_username" {
  description = "The username for the CloudSQL store"
  default     = "admin"
  type        = string
}
variable "database_password" {
  description = "The password for the CloudSQL store"
  default     = ""
  type        = string
}

# if you enable the deploy_db option, the recipe will
# create a new CloudSQL MySQL instance and then use it for this
# ZenServer. If disabled, you have to supply connection details
# in the section below.
variable "deploy_db" {
  description = "Should the recipe create an CloudSQL instance?"
  default     = true
  type        = bool
}
variable "cloudsql_name" {
  description = "The name for the CloudSQL store"
  default     = "zenmlserver"
  type        = string
}
variable "db_name" {
  description = "The name for the database"
  default     = "zenmlserver"
  type        = string
}

variable "db_instance_tier" {
  description = "The instance class to use for the database"
  default     = "db-n1-standard-1"
  type        = string
}

variable "db_disk_size" {
  description = "The allocated storage in gigabytes"
  default     = 10
  type        = number
}

# If you haven't enabled the deploy_db option, provide
# the following value in the values.tfvars.json file.
variable "database_url" {
  description = "The URL for the AWS RDS instance"
  default     = ""
  type        = string
}
variable "database_ssl_ca" {
  description = "The server ca for the AWS RDS instance"
  default     = ""
  type        = string
}
variable "database_ssl_cert" {
  description = "The client cert for the AWS RDS instance"
  default     = ""
  type        = string
}
variable "database_ssl_key" {
  description = "The client key for the AWS RDS instance"
  default     = ""
  type        = string
}
variable "database_ssl_verify_server_cert" {
  description = "Should SSL be verified?"
  default     = true
  type        = bool
}


# Enable secrets manager API. Listing services might need elevated permissions.
# Disable this if you don't have the ListServices permission.
variable "enable_secrets_manager_api" {
  description = "Enable the secrets manager API"
  default     = true
  type        = bool
}

# set to true if you don't already have an nginx ingress
# controller in your cluster
variable "create_ingress_controller" {
  description = "set to true  if you want the recipe to create an ingress controller in your cluster"
  default     = false
  type        = bool
}

# if you already have an ingress controller, supply it's URL
variable "ingress_controller_ip" {
  description = "The hostname for the ingress controller on your cluster"
  default     = ""
  type        = string
}
variable "ingress_tls" {
  description = "Whether to enable tls on the ingress or not"
  default     = false
  type        = bool
}
variable "ingress_tls_generate_certs" {
  description = "Whether to enable tls certificates or not"
  default     = false
  type        = bool
}
variable "ingress_tls_secret_name" {
  description = "Name for the Kubernetes secret that stores certificates"
  default     = "zenml-tls-certs"
  type        = string
}

variable "zenmlserver_image_repo" {
  description = "The repository to use for the zenmlserver docker image."
  default     = "zenmldocker/zenml-server"
  type        = string
}
variable "zenmlserver_image_tag" {
  description = "The tag to use for the zenmlserver docker image."
  default     = "latest"
  type        = string
}

# variables for creating a ZenML stack configuration file
variable "zenml-version" {
  description = "The version of ZenML being used"
  default     = "0.20.0"
  type        = string
}