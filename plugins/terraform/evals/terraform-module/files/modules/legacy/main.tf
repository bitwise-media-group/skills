variable "name" {
  description = "Bucket name prefix."
  type        = string
}

resource "aws_s3_bucket" "main" {
  bucket_prefix = var.name
}

output "bucket" {
  description = "Name of the bucket."
  value       = aws_s3_bucket.main.bucket
}
