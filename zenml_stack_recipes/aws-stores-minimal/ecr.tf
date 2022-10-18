# add an optional container registry
resource "aws_ecr_repository" "zenml-ecr-repository" {
  name                 = local.ecr.name
  image_tag_mutability = "MUTABLE"
  count                = local.ecr.enable_container_registry ? 1 : 0
  tags                 = local.tags
}