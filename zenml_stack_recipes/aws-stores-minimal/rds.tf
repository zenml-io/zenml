module "metadata_store" {
  source = "terraform-aws-modules/rds/aws"

  identifier = "${local.prefix}-${local.rds.rds_name}"

  engine            = local.rds.db_type
  engine_version    = local.rds.db_version
  instance_class    = "db.t3.micro"
  allocated_storage = 5

  db_name                = local.rds.db_name
  username               = var.metadata-db-username
  password               = var.metadata-db-password
  create_random_password = var.metadata-db-password == "" ? true : false
  port                   = "3306"

  # configure access
  publicly_accessible = true

  # DB subnet group
  create_db_subnet_group = true
  subnet_ids             = module.vpc.public_subnets
  skip_final_snapshot    = true

  iam_database_authentication_enabled = false

  # we've added MySQL ingress rules to 
  # this sg so we're using it here
  vpc_security_group_ids = [module.vpc.default_security_group_id]

  # DB parameter group
  family = "mysql8.0"

  # DB option group
  major_engine_version = "8.0"

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