output "ecr_repository_url" {
  value       = aws_ecr_repository.churn_api.repository_url
  description = "Push your image here"
}

output "cluster_name" {
  value       = module.eks.cluster_name
  description = "Use: aws eks update-kubeconfig --name <this> --region <region>"
}

output "configure_kubectl" {
  value = "aws eks update-kubeconfig --name ${module.eks.cluster_name} --region ${var.region}"
}
