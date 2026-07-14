# The SIMPLE resource students read line-by-line to learn Terraform basics:
# one resource, clear arguments, real AWS output. Stores the churn-api image.
resource "aws_ecr_repository" "churn_api" {
  name                 = "churn-api"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}
