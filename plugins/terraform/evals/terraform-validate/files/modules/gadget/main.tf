resource "aws_s3_bucket" "main" {
  bucket_prefix = var.name
}
