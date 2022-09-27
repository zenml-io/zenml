variable "prefix" {
  description = "The prefix to use for all AWS resource names"
  default     = "zenmlserver"
  type        = string
}

variable "region" {
  description = "The region for your AWS resources"
  default     = "eu-west-1"
  type        = string
}

variable "zenmlserver_namespace" {
  description = "The namespace to install the ZenML server Helm chart in"
  default     = "terraform-server"
  type        = string
}
variable "kubectl_config_path" {
  description = "The path to the kube config"
  default     = ""
  type        = string
}

# If you want a new RDS, choose a name and a password. If you already
# have an instance, provide the name and the password here too.
variable "rds_db_username" {
  description = "The username for the AWS RDS metadata store"
  default     = "admin"
  type        = string
}
variable "rds_db_password" {
  description = "The password for the AWS RDS metadata store"
  default     = ""
  type        = string
}

# if you enable the create_rds option, the recipe will
# create a new RDS MySQL instance and then use it for this
# ZenServer. If disabled, you have to supply connection details
# in the section below.
variable "create_rds" {
  description = "Should the recipe create an RDS instance?"
  default     = true
  type        = bool
}
variable "rds_name" {
  description = "The name for the AWS RDS metadata store"
  default     = "zenmlserver"
  type        = string
}
variable "db_name" {
  description = "The name for the AWS RDS database"
  default     = "zenmlserver"
  type        = string
}
variable "db_type" {
  description = "The type for the AWS RDS database"
  default     = "mysql"
  type        = string
}
variable "db_version" {
  description = "The version for the AWS RDS database"
  default     = "8.0.28"
  type        = string
}
variable "db_instance_class" {
  description = "The instance class to use for the database"
  default     = "db.t3.micro"
  type        = string
}

variable "db_allocated_storage" {
  description = "The allocated storage in gigabytes"
  default     = 5
  type        = number
}

# If you haven't enabled the create_rds option, provide
# the following value in addition to setting the username and
# password in the values.tfvars.json file.
variable "rds_url" {
  description = "The URL for the AWS RDS instance"
  default     = ""
  type        = string
}
variable "rds_sslCa" {
  description = "The server ca for the AWS RDS instance"
  default     = ""
  type        = string
}
variable "rds_sslCert" {
  description = "The client cert for the AWS RDS instance"
  default     = ""
  type        = string
}
variable "rds_sslKey" {
  description = "The client key for the AWS RDS instance"
  default     = ""
  type        = string
}
variable "rds_sslVerifyServerCert" {
  description = "Should SSL be verified?"
  default     = true
  type        = bool
}

variable "ingress_path" {
  description = "The path on the Ingress URL to expose ZenML at"
  default     = "zenmlhihi"
  type        = string
}

# set to true if you don't already have an nginx ingress
# controller in your cluster
variable "create_ingress_controller" {
  description = "set to true  if you want the recipe to create an ingress controller in your cluster"  
  default     = true
  type        = bool
}
# if you already have an ingress controller, supply it's URL
variable "ingress_controller_hostname" {
  description = "The URL for the ingress controller on your cluster"
  default     = ""
  type        = string
}

# variables for creating a ZenML stack configuration file
variable "zenml-version" {
  description = "The version of ZenML being used"
  default     = "0.13.2"
  type        = string
}