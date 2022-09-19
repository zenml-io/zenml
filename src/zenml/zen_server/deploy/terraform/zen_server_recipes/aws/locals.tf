# config values to use across the module
locals {
  prefix = "demo"
  region = "eu-west-1"

  rds = {
    # if you enable the create_rds option, the recipe will
    # create a new RDS MySQL instance and then use it for this
    # ZenServer. If disabled, you have to supply connection details
    # in the section below.
    create_rds = true
    rds_name   = "zenml-rds"
    db_name    = "zenmldb"
    db_type    = "mysql"
    db_version = "8.0.28"

    # If you haven't enabled the create_rds option, provide
    # the following value in addition to setting the username and
    # password in the values.tfvars.json file.
    hostname    = ""
    server_ca   = ""
    client_cert = ""
    client_key  = ""
  }

  tags = {
    "managedBy"   = "terraform"
    "application" = local.prefix
  }
}