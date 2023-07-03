# random string for the RDS instance name
resource "random_string" "rds_suffix" {
  count  = var.deploy_db ? 1 : 0
  length = 4
  upper  = false
  special = false
}

module "metadata_store" {
  source  = "terraform-aws-modules/rds/aws"
  version = "5.9.0"
  count   = var.deploy_db ? 1 : 0

  identifier = "${var.name}${var.rds_name}${random_string.rds_suffix[0].result}"

  engine            = var.db_type
  engine_version    = var.db_version
  instance_class    = var.db_instance_class
  allocated_storage = var.db_allocated_storage

  db_name                = var.db_name
  username               = var.database_username
  password               = var.database_password
  create_random_password = var.database_password == "" ? true : false
  port                   = "3306"

  # configure access
  publicly_accessible = true

  # DB subnet group
  create_db_subnet_group = true
  subnet_ids             = module.vpc[0].public_subnets
  skip_final_snapshot    = true

  iam_database_authentication_enabled = false

  # we've added MySQL ingress rules to 
  # this sg so we're using it here
  vpc_security_group_ids = [module.vpc[0].default_security_group_id]

  # DB parameter group
  family = "mysql5.7"

  # DB option group
  major_engine_version = "5.7"

  tags = {
    Owner       = "user"
    Environment = "zenml-env"
  }

  parameters = [
    {
      name  = "character_set_client"
      value = "utf8mb4"
    },
    {
      name  = "character_set_server"
      value = "utf8mb4"
    }
  ]
}