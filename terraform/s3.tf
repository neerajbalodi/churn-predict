resource "aws_s3_bucket" "models" {
  bucket = "${var.cluster_name}-models"
}
