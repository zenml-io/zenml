# output for s3 bucket
output "s3-bucket-path" {
  value       = "s3://${aws_s3_bucket.zenml-artifact-store.bucket}"
  description = "The S3 bucket path for storing your artifacts"
}

# outputs for the metadata store
output "metadata-db-host" {
  value = module.metadata_store.db_instance_address
}
output "metadata-db-username" {
  value     = module.metadata_store.db_instance_username
  sensitive = true
}
output "metadata-db-password" {
  value     = module.metadata_store.db_instance_password
  sensitive = true
}

# output for container registry
output "container-registry-URI" {
  value = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${local.region}.amazonaws.com"
}
output "ecr-registry-name" {
  value       = aws_ecr_repository.zenml-ecr-repository[0].name
  description = "The ECR registry repository for storing your images"
}

# output the name of the stack YAML file created
output "stack-yaml-path" {
  value = local_file.stack_file.filename
}