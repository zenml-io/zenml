# config values to use across the module
locals {
  prefix = "svccli"
  region = "eu-west-1"

  vpc = {
    name = "vpc"
  }

  s3 = {
    name = "artifact-store"
  }

  ecr = {
    name                      = "zenml-kubernetes"
    enable_container_registry = true
  }

  rds = {
    rds_name   = "metadata"
    db_name    = "zenmldb"
    db_type    = "mysql"
    db_version = "8.0.28"
  }

  tags = {
    "managedBy"   = "terraform"
    "application" = local.prefix
  }
}