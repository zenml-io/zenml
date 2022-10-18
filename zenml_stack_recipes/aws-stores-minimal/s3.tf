# creste s3 bucket for storing artifacts
resource "aws_s3_bucket" "zenml-artifact-store" {
  bucket        = "${local.prefix}-${local.s3.name}"
  force_destroy = true

  tags = merge(
    local.tags,
    {
      name = "zenml-artifact-store"
    }
  )
}

resource "aws_s3_bucket_acl" "example" {
  bucket = aws_s3_bucket.zenml-artifact-store.id
  acl    = "private"
}

# block public access to the bucket
resource "aws_s3_bucket_public_access_block" "example" {
  bucket = aws_s3_bucket.zenml-artifact-store.id

  block_public_acls   = true
  block_public_policy = true
}